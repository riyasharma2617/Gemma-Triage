# Gemma Triage — End-to-End Pipeline Walkthrough
*Following Medic Riya Shah through a single triage decision at 3:14 AM*

---

## The Scenario

> 3:14 AM. Riya finds a man half-buried in rubble. She has a $700 Android phone, a first-aid kit, and four exhausted volunteers. No signal bars. No oxygen tank on hand. 14 patients already tagged. She needs to classify this patient, get spoken instructions she can act on immediately, and be able to ask follow-up questions as the situation changes — all without looking at a screen.

---

## Phase A — Initial Triage

### Step 1 — Button Press → ViewModel

Riya holds down the **RECORD** button.

`MainActivity.kt` catches the `ACTION_DOWN` touch event:

```kotlin
MotionEvent.ACTION_DOWN -> viewModel.startListening()
```

`TriageViewModel.startListening()` checks the model is ready, resets state to `Idle`, then fires the speech recognizer.

---

### Step 2 — Voice Capture → Android Speech Engine

`SpeechToTextManager.startListening()` opens Android's `SpeechRecognizer` with one critical flag:

```kotlin
putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
```

The mic captures 16kHz PCM audio. No Google servers contacted. No network activity.

Riya speaks:
> *"Male, approximately 40 years old. Breathing 38 times per minute. Radial pulse is absent. Not following my commands."*

She releases the button — `ACTION_UP` → `viewModel.stopListening()` — and the recognizer finalizes.

---

### Step 3 — Text Emitted → ViewModel Pipeline

`onResults()` fires:

```kotlin
_state.value = STTState.Result(
    "Male, approximately 40 years old. Breathing 38 times per minute. Radial pulse is absent. Not following my commands."
)
```

`TriageViewModel` observes `STTState.Result`, emits `TriageUiState.Transcribing(text)`, then immediately calls `runInference(transcription)` → emits `TriageUiState.Analyzing`.

On Riya's screen: her words appear, then the progress bar pulses — *"Gemma 4 analyzing..."*

---

### Step 4 — Prompt Construction

`PromptBuilder.buildPrompt(context, patientDescription)` assembles three sections:

**Section A — System prompt** (from `assets/prompts/system_prompt.txt`):
```
You are a certified emergency medical triage AI using the START protocol.
RED: resp >30/min, absent radial pulse, altered mental status.
Return valid JSON matching the full schema including immediateSteps,
monitoringChecklist, warningSigns, spokenSummary, smsPayload.
```

**Section B — 2 random few-shot examples** from `few_shot_examples.json` — shows Gemma the exact expanded JSON format with all fields populated.

**Section C — Riya's patient**, wrapped in Gemma chat template:
```
<start_of_turn>user
Analyze this patient: Male, approximately 40 years old...
<end_of_turn>
<start_of_turn>model
```

---

### Step 5 — On-Device Inference (The Core)

```kotlin
val rawOutput = llmInference.generateResponse(prompt)
```

**No network. No API. Nothing leaves the phone.**

MediaPipe LlmInference loads the prompt into the INT4-quantized Gemma 4 E2B model (~1.3GB in device RAM) and runs GPU-accelerated inference via OpenGL ES.

Gemma applies START logic internally:

| Criterion | Finding | Decision |
|---|---|---|
| Respiratory rate | 38/min | >30 threshold → **RED** |
| Radial pulse | Absent | Perfusion failure → **RED** |
| Mental status | Not following commands | Altered → **RED** |

Gemma generates the full expanded JSON (~2–4 seconds):

```json
{
  "triageCode": "RED",
  "confidence": 0.97,
  "reasoning": "Three RED criteria met: respiratory rate 38/min exceeds threshold, absent radial pulse indicates perfusion failure, altered mental status confirmed.",
  "spokenSummary": "RED. Immediate. This patient has three critical signs and needs intervention right now.",
  "immediateSteps": [
    "Step 1: Tilt his head back and lift the chin — open the airway. Look for chest rise.",
    "Step 2: Apply firm direct pressure to any visible bleeding with both hands. Do not let go.",
    "Step 3: Keep him completely still — assume spinal injury until proven otherwise.",
    "Step 4: Have someone prepare for immediate evacuation transport."
  ],
  "monitoringChecklist": [
    "Recheck radial pulse every 60 seconds.",
    "If breathing rate drops below 8 or rises above 45 — reassess immediately.",
    "Watch for skin turning pale or blue — this means worsening shock."
  ],
  "warningSigns": [
    "If breathing stops: give one rescue breath every 5 seconds.",
    "If he becomes completely unresponsive: shout for help and reassess tag."
  ],
  "smsPayload": "TRG|R|97|Open airway;Direct pressure;Spinal precaution;Evacuate"
}
```

---

### Step 6 — JSON Parsing → TriageResult

`GemmaInferenceEngine.parseTriageResultFromJson()`:

1. Finds the first `{` and last `}` — strips any preamble text
2. Gson deserializes into `RawTriageResult`
3. `"RED"` → `TriageCode.RED` enum
4. Confidence clamped to `[0.0, 1.0]`
5. Returns typed `TriageResult` with all fields populated

---

### Step 7 — Output Fan-Out (SMS fires once, here)

`TriageOutputManager.process(result, transcription)` runs on `Dispatchers.IO`:

**7a — Room Database**
```kotlin
db.triageDao().insert(TriageRecord(
    timestamp          = System.currentTimeMillis(),
    patientDescription = "Male, approximately 40...",
    triageCode         = "RED",
    confidence         = 0.97,
    isTransmitted      = true
))
```

**7b — SMS (pre-computed by Gemma, sent once)**
```
TRG|R|97|Open airway;Direct pressure;Spinal precaution;Evacuate
```
`QueueManager` dispatches via `SmsManager.sendTextMessage()` → satellite modem → Coordinator HQ 200 km away.

**The conversation that follows never touches SMS. This fires once and is done.**

---

### Step 8 — UI Update

`TriageViewModel` emits `TriageUiState.ResultReady`. `MainActivity` renders:

```
┌─────────────────────────────────────────┐
│           RED — IMMEDIATE               │  ← #D32F2F red
│             Confidence: 97%             │
│─────────────────────────────────────────│
│ Three RED criteria met: resp 38/min,    │
│ absent radial pulse, altered MS.        │
│─────────────────────────────────────────│
│ IMMEDIATE STEPS                         │
│ 1. Tilt head back, lift chin. Chest     │
│    rise?                                │
│ 2. Direct pressure on bleeding.         │
│    Both hands. Don't let go.            │
│ 3. Keep still — assume spinal.          │
│ 4. Prepare immediate evacuation.        │
│─────────────────────────────────────────│
│ MONITOR                                 │
│ • Radial pulse every 60s               │
│ • Resp drops <8 or rises >45: reassess │
│ • Pale/blue skin = worsening shock     │
└─────────────────────────────────────────┘
  [ 🔊 Speaking... ] [ NEXT PATIENT ]
```

---

## Phase B — Voice Output (Hands-Free Instructions)

### Step 9 — TTS Reads the Result Aloud

`TextToSpeechManager.speak()` fires immediately after `ResultReady`. No button needed.

The phone speaks in this sequence — Riya does not need to look at the screen:

> **"RED. IMMEDIATE."** ← loud, short, first
>
> *"This patient has three critical signs and needs intervention right now."* ← `spokenSummary`
>
> *"Step 1: Tilt his head back and lift the chin — open the airway. Look for chest rise."*
> *"Step 2: Apply firm direct pressure to any visible bleeding with both hands. Do not let go."*
> *"Step 3: Keep him completely still — assume spinal injury until proven otherwise."*
> *"Step 4: Have someone prepare for immediate evacuation transport."*

Speech rate: 0.85× (slightly slower than default for field noise conditions).

`TTSState.Done` is emitted when the last step finishes speaking.

---

## Phase C — Follow-Up Conversation Loop

### Step 10 — Mic Auto-Opens for Follow-Up

`TriageViewModel` observes `TTSState.Done` → auto-emits `TriageUiState.FollowUpListening`.

The mic opens automatically. The UI shows:

```
🎙  Ask a follow-up question or say "next patient"
```

Riya doesn't tap anything. She just speaks.

---

### Step 11 — Riya's First Follow-Up Question

> *"I don't have oxygen. What else can I do?"*

`SpeechRecognizer` returns text. `ConversationManager.buildFollowUpPrompt()` assembles:

```
[Original patient context]
Male, approximately 40 years old. Breathing 38 times per minute...

[Initial classification]
triageCode: RED | confidence: 0.97
reasoning: Three RED criteria met...

[Conversation so far]
(empty — first follow-up)

[Thinking scaffolding]
Think step by step through the patient's current condition,
the specific constraint or new information stated,
and what clinical alternatives are available.
Then give a clear, actionable answer in plain language.

[New question]
Riya: I don't have oxygen. What else can I do?
```

Temperature raised to `0.3f`. MaxTokens raised to `768` — follow-ups need more reasoning space.

---

### Step 12 — Gemma Thinks, Then Answers

Gemma runs in **thinking mode** — it reasons internally before responding:

```
<thinking>
Patient: RED — absent pulse, resp 38/min, altered MS.
Constraint: No oxygen available.
Oxygen alternatives:
- Positioning: Head-tilt chin-lift maximises airway patency → passive oxygenation
- Rescue breathing: If rate deteriorates, mouth-to-mouth provides ~16% O2
- Recovery position: If unconscious but breathing, lateral position maintains airway
- The absent radial pulse is the bigger concern — suggests haemorrhagic shock
  → positioning (legs elevated if no spinal concern) improves venous return
Primary answer: airway position + rescue breathing as backup + shock positioning
</thinking>

Without oxygen, your main tool is position. Keep his head tilted back and chin 
lifted at all times — this maximises how much air reaches his lungs passively. 
If his breathing rate drops below 8, start mouth-to-mouth: one slow breath every 
5 seconds. Also, if there's no spinal concern, elevate his legs about 30 
centimetres — this pushes blood back toward his heart and buys time against shock.
```

The `<thinking>` block is stripped before TTS. Only the final answer is spoken.

---

### Step 13 — TTS Reads the Answer Aloud

> *"Without oxygen, your main tool is position. Keep his head tilted back and chin lifted at all times — this maximises how much air reaches his lungs passively. If his breathing rate drops below 8, start mouth-to-mouth: one slow breath every 5 seconds. Also, if there's no spinal concern, elevate his legs about 30 centimetres — this pushes blood back toward his heart and buys time against shock."*

UI conversation panel updates:

```
─────────────────────────────────────────
Riya:  "I don't have oxygen. What else?"
Gemma: "Without oxygen, your main tool
        is position. Keep head tilted..."
─────────────────────────────────────────
```

Mic re-opens automatically. Loop continues.

---

### Step 14 — Second Follow-Up (Situation Changes)

> *"He just started seizing."*

`ConversationManager` now includes the full exchange history in the next prompt. Gemma sees:
- The original RED classification
- The oxygen constraint answer
- The new development: seizure

Gemma thinks through: *seizure on a RED patient, possible TBI or hypoxia-induced, resource-limited setting...*

Response:
> *"Seizure alert. Do not restrain him — let the seizure run. Clear any hard objects away from his body and time it on your watch. If it goes beyond 2 minutes, that is a critical escalation — flag him for the next available transport regardless of queue position. After the seizure stops, immediately recheck his airway — seizures often cause the tongue to block the throat."*

---

### Step 15 — Exit: Next Patient

Riya says *"next patient"* aloud — the STT detects the keyword.

`TriageViewModel`:
- Clears conversation history
- Increments patient count to 15
- Resets to `TriageUiState.Idle`
- TTS: *"Ready for next patient."*

---

## Complete Flow at a Glance

```
━━━ PHASE A: INITIAL TRIAGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Riya presses RECORD
  → SpeechToTextManager (offline STT, EXTRA_PREFER_OFFLINE=true)
  → "Male, 40, breathing 38/min, absent pulse, won't follow commands"
  → PromptBuilder: system_prompt + 2 few-shot examples + patient
  → MediaPipe LlmInference (Gemma 4 E2B INT4, on-device GPU, ~3s)
  → Expanded JSON: triageCode + spokenSummary + immediateSteps
                   + monitoringChecklist + warningSigns + smsPayload
  → TriageOutputManager:
      ├─ Room DB: TriageRecord inserted          (audit trail)
      └─ smsPayload → QueueManager → SmsManager → Satellite → HQ
                                                  ↑ FIRES ONCE ONLY

━━━ PHASE B: VOICE OUTPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → TextToSpeechManager.speak():
      "RED. IMMEDIATE."
      spokenSummary (2 sentences)
      immediateSteps (4 steps, plain language)
  → TTSState.Done emitted

━━━ PHASE C: CONVERSATION LOOP (repeats until "next patient") ━━━

  → Mic auto-opens → FollowUpListening
  → Riya speaks follow-up question
  → ConversationManager.buildFollowUpPrompt():
      original patient + classification + history + thinking scaffolding
  → GemmaInferenceEngine (temp 0.3f, 768 tokens, thinking mode)
  → Plain text answer (thinking block stripped)
  → ConversationManager stores exchange in history
  → TextToSpeechManager.speak(answer)
  → Mic auto-opens again → loop

  EXIT: "next patient" keyword OR NEXT PATIENT button
    → conversation history cleared
    → patient count +1
    → Idle state
    → TTS: "Ready for next patient."
```

---

## Key Numbers

| Metric | Value |
|---|---|
| Initial triage inference time | ~3 seconds |
| Follow-up inference time | ~4–6 seconds (thinking mode) |
| Model size on disk | ~1.3 GB (INT4 quantized) |
| Network bytes during session | 0 |
| SMS payload size | ≤ 160 characters (once per patient) |
| Initial triage temperature | 0.1 (near-deterministic) |
| Follow-up temperature | 0.3 (adaptive reasoning) |
| Conversation history scope | Current patient only (cleared on next patient) |
| Riya's phone | $700 Android |
| Signal bars required | 0 |

---

*No internet. No cloud. No server. Gemma 4 runs on a $700 Android phone in a rubble field. It classifies, speaks the instructions aloud, listens to follow-up questions, thinks through constraints, and keeps talking Riya through the patient until she says "next patient" — all at 3 AM, with zero signal bars.*
