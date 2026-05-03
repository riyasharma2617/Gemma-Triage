# Gemma Triage — End-to-End Pipeline Walkthrough
*Following Medic Riya Shah through a single triage decision at 3:14 AM*

---

## The Scenario

> 3:14 AM. Riya finds a man half-buried in rubble. She can't feel a radial pulse. He's breathing but fast, and won't respond when she calls his name. 14 patients already tagged. Phone in airplane mode. Zero bars.

---

## Step 1 — Button Press → ViewModel

Riya holds down the **RECORD** button.

`MainActivity.kt` catches the `ACTION_DOWN` touch event:

```kotlin
MotionEvent.ACTION_DOWN -> viewModel.startListening()
```

`TriageViewModel.startListening()` first checks the model is loaded, then resets state to `Idle` and fires the speech recognizer.

---

## Step 2 — Voice Capture → Android Speech Engine

`SpeechToTextManager.startListening()` opens Android's `SpeechRecognizer` with one critical flag:

```kotlin
putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
```

This routes audio through the **locally-installed English speech model** — no Google servers involved. The mic captures 16kHz PCM audio (the same format `AudioCaptureManager` uses), and the OS VAD (voice activity detection) automatically trims silence.

Riya speaks:
> *"Male, approximately 40 years old. Breathing 38 times per minute. Radial pulse is absent. Not following my commands."*

She releases the button — `ACTION_UP` → `viewModel.stopListening()` — and the recognizer finalizes.

---

## Step 3 — Text Emitted → ViewModel Pipeline

`onResults()` fires inside `SpeechToTextManager`:

```kotlin
_state.value = STTState.Result(
    "Male, approximately 40 years old. Breathing 38 times per minute. Radial pulse is absent. Not following my commands."
)
```

The `TriageViewModel` is `collectLatest`-ing that StateFlow. It sees `STTState.Result`, checks the text isn't blank, then:

```
UI State: Transcribing("Male, approximately 40 years old...")
     ↓
runInference(transcription) called
     ↓
UI State: Analyzing
```

On Riya's screen: the text she spoke appears verbatim, then the progress bar and *"Gemma 4 analyzing..."* pulse into view.

---

## Step 4 — Prompt Construction

`GemmaInferenceEngine.runTriageInference()` calls `PromptBuilder.buildPrompt(context, patientDescription)`.

The builder assembles three sections:

**Section A — System prompt** (loaded from `assets/prompts/system_prompt.txt`):

```
You are a certified emergency medical triage AI operating under the START protocol...
RED (Immediate): Resp >30/min, absent radial pulse, altered mental status...
Respond with valid JSON ONLY.
```

**Section B — 2 random few-shot examples** (sampled from `few_shot_examples.json`'s 13 cases). For example:

```
<user>  Analyze this patient: Young woman, breathing 38 times a minute...
<model> {"triageCode":"RED","confidence":0.97,"reasoning":"Respiratory rate >30/min..."}
```

**Section C — Riya's actual patient:**

```
<user>  Analyze this patient: Male, approximately 40 years old. Breathing 38 times per minute...
<model>   ← Gemma writes here
```

The Gemma chat template wraps everything:

```
<start_of_turn>system
[START protocol rules]
<end_of_turn>
<start_of_turn>user
[example 1 patient]
<end_of_turn>
<start_of_turn>model
[example 1 JSON]
<end_of_turn>
<start_of_turn>user
Analyze this patient: Male, 40, breathing 38/min, absent radial pulse...
<end_of_turn>
<start_of_turn>model
```

The few-shot examples + low temperature (0.1) train Gemma's response format in-context, so it reliably produces JSON rather than prose.

---

## Step 5 — On-Device Inference (The Core)

```kotlin
val rawOutput = llmInference.generateResponse(prompt)
```

This call **never leaves the phone.** MediaPipe's `LlmInference` engine:

1. **Loads the prompt tokens** into the INT4-quantized Gemma 4 E2B model (~1.3GB in device RAM)
2. **Runs GPU-accelerated forward passes** via OpenGL ES on the phone's GPU
3. **Autoregressively generates tokens** one at a time until it produces a complete JSON object or hits the 512-token cap
4. **Returns raw text** — typically within 2–4 seconds on a mid-range Android

Gemma internally applies START logic:

| Criterion | Patient Finding | Decision |
|---|---|---|
| Respiratory rate | 38/min | >30 threshold → **RED** |
| Radial pulse | Absent | Perfusion failure → **RED** |
| Mental status | Not following commands | Altered → **RED** |

Raw output from Gemma:

```json
{
  "triageCode": "RED",
  "confidence": 0.97,
  "reasoning": "Three RED criteria met: respiratory rate 38/min exceeds 30/min threshold, absent radial pulse indicates perfusion failure, altered mental status (not following commands). Immediate life-saving intervention required.",
  "recommendedActions": [
    "Secure airway immediately",
    "Control any external hemorrhage",
    "IV access — two large-bore cannulas",
    "Priority transport — do not delay"
  ]
}
```

---

## Step 6 — JSON Parsing → TriageResult

`GemmaInferenceEngine.parseTriageResultFromJson()` handles the raw string:

1. Finds the first `{` and last `}` — strips any model preamble text
2. `Gson.fromJson()` deserializes into `RawTriageResult` (String fields)
3. Converts `"RED"` string → `TriageCode.RED` enum via `TriageCode.valueOf()`
4. Clamps confidence to `[0.0, 1.0]`
5. Returns a typed `TriageResult`

If Gemma produced malformed JSON (rare with few-shot + low temp), it returns `TriageCode.UNKNOWN` with the raw output as the reasoning — never crashes.

---

## Step 7 — Output Fan-Out

`TriageOutputManager.process(result, transcription)` runs on `Dispatchers.IO`:

### 7a — Room Database (Audit Trail)

```kotlin
db.triageDao().insert(TriageRecord(
    timestamp         = System.currentTimeMillis(),  // 3:14:33 AM
    patientDescription = "Male, approximately 40...",
    triageCode        = "RED",
    confidence        = 0.97,
    isTransmitted     = false
))
```

Every triage decision is persisted locally. If Riya's phone is later recovered from mud, the full session audit trail is intact.

### 7b — SMS Compression → Dispatch

`SMSFormatter.formatForSMS(result)` compresses the result to 160 characters:

```
TRG|R|97|Secure airway immediately;Control any external hemorrh;IV access
```

Format: `TRG | code initial | confidence% | actions (max 20 chars each, semicolon-delimited)`

`QueueManager.enqueue(sms)` attempts `SmsManager.sendTextMessage()` to the coordinator number. If the satellite modem isn't responding, it queues with retry logic (exponential backoff, max 3 attempts).

---

## Step 8 — UI Update

`TriageViewModel` emits `TriageUiState.ResultReady(result, transcription)`.

`MainActivity` renders:

```
┌─────────────────────────────────┐
│        RED — IMMEDIATE          │  ← #D32F2F red, 28sp bold
│          Confidence: 97%        │
│─────────────────────────────────│
│ Three RED criteria met: resp    │
│ rate 38/min, absent radial      │
│ pulse, altered mental status.   │
│                                 │
│ 1. Secure airway immediately    │
│ 2. Control external hemorrhage  │
│ 3. IV access — two large-bore   │
│ 4. Priority transport           │
└─────────────────────────────────┘
      [ DISPATCH VIA SMS ]

Patients Assessed: 15
```

Total time from button release to result on screen: **~4 seconds.**
Zero bytes sent to any server. Zero network calls made.

---

## Complete Flow at a Glance

```
Riya presses RECORD
        │
        ▼
MainActivity (ACTION_DOWN)
        │
        ▼
TriageViewModel.startListening()
        │
        ▼
SpeechToTextManager
  → Android SpeechRecognizer (OFFLINE, EXTRA_PREFER_OFFLINE=true)
  → VAD detects speech end on button release
  → STTState.Result("Male, 40, breathing 38/min, absent pulse, altered MS")
        │
        ▼
TriageViewModel.runInference(text)
  → UI: Analyzing (progress bar visible)
        │
        ▼
PromptBuilder.buildPrompt(context, text)
  → system_prompt.txt    — START protocol rules + JSON schema
  → few_shot_examples.json — 2 random in-context examples
  → Gemma chat template assembled
        │
        ▼
MediaPipe LlmInference.generateResponse(prompt)
  → Gemma 4 E2B INT4  (~1.3GB, on-device GPU via OpenGL ES)
  → 2–4 seconds, no network activity
  → Raw JSON string output
        │
        ▼
GemmaInferenceEngine.parseTriageResultFromJson()
  → Strip preamble, extract JSON
  → Gson deserialize → TriageCode.RED enum
  → TriageResult(RED, 0.97, reasoning, actions[])
        │
        ├─────────────────────────────────────┐
        ▼                                     ▼
Room Database                          SMSFormatter
TriageRecord inserted                  "TRG|R|97|Secure airway..."
(local audit trail, encrypted)                │
                                       QueueManager
                                       SmsManager.sendTextMessage()
                                       → Satellite modem → Coordinator HQ
        │
        ▼
TriageViewModel → TriageUiState.ResultReady
        │
        ▼
MainActivity
  → RED card (#D32F2F), confidence 97%, reasoning, 4 actions
  → Patient count increments to 15
```

---

## Key Numbers

| Metric | Value |
|---|---|
| Time from button release to result | ~4 seconds |
| Model size on disk | ~1.3 GB (INT4 quantized) |
| Network bytes transmitted | 0 |
| SMS payload size | ≤ 160 characters |
| Inference temperature | 0.1 (near-deterministic) |
| Few-shot examples in prompt | 2 (randomly sampled from 13) |
| Room DB records this session | 15 (one per patient) |

---

*No internet. No API call. No cloud. Gemma 4 runs entirely on a $200 Android phone — in a rubble field, at 3 AM, with zero signal bars.*
