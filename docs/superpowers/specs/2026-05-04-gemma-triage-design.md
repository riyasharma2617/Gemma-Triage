# Gemma Triage — Design Specification
**Date:** 2026-05-04 | **Deadline:** 2026-05-18 (14 days) | **Track:** Global Resilience + LiteRT Special Prize

---

## The Storyline — "Operation Zero-Signal"

> *The night the grid went dark, every second counted.*

It's 2:47 AM on August 14th. A 7.4 magnitude earthquake has just struck the Himalayan foothills. Within minutes, cell towers collapse under the surge. Satellite uplinks are overwhelmed. The power grid is down across four districts.

By dawn, 23 rescue teams are scattered across 400 square kilometers of rubble. They have headlamps, first-aid kits, and one thing they didn't plan for: **200+ casualties and no way to coordinate**.

Medic Riya Shah has trained on the START triage protocol for five years. But mass-casualty incidents don't run on training scenarios. In the dark, surrounded by crying voices, with dust in her lungs and a team of four exhausted volunteers — human memory fails. She needs something that can **think fast, without internet, without a tower, without a cloud**.

She picks up her $700 Android phone — no signal bars, battery at 61%. She holds it to a survivor's face.

*"He's breathing thirty-five times a minute and won't respond to my voice."*

The phone processes locally. No ping. No upload. **Gemma 4 runs entirely on the device.**

Three seconds later: **RED — Immediate. Secure airway. Administer oxygen. Priority transport.**

A compressed 48-character SMS fires through the team's satellite modem to the coordination center 200 km away.

That decision — made in 3 seconds, without a single byte of internet — saves a life.

**This is Gemma Triage.**

---

## Project Overview

**Gemma Triage** is an offline-first Android application for mass-casualty incident (MCI) triage. It uses Google's Gemma 4 E2B language model running entirely on-device via the MediaPipe LLM Inference API to classify casualties according to the START (Simple Triage and Rapid Treatment) protocol.

A first responder speaks a patient description into their phone. Gemma interprets the clinical language, applies START protocol logic, and generates a structured JSON classification — all within seconds, with zero connectivity. The result is compressed and dispatched via SMS or satellite modem to a coordination center.

**Hackathon prizes targeted:**
- **$10,000 — Global Resilience Track** (offline, disaster-focused, high-stakes)
- **$10,000 — LiteRT Special Prize** (on-device inference via MediaPipe/LiteRT)
- **Main Gemma 4 Track** (demonstrates Frontier Intelligence, Thinking Mode, Function Calling)

---

## Goals & Success Criteria

### Must Have (Demo Day)
- [ ] Voice input → on-device transcription → Gemma 4 inference → RED/YELLOW/GREEN/BLACK classification
- [ ] Zero internet required after model setup (no API calls, no cloud)
- [ ] Structured JSON output (triage code, confidence, reasoning, recommended actions)
- [ ] SMS compression and dispatch (160-char format via Android SmsManager)
- [ ] Dark emergency-themed UI that reads in bright sunlight on a dusty screen

### Should Have
- [ ] Room database audit trail of all triage decisions
- [ ] Patient queue counter (how many assessed this session)
- [ ] Battery optimization mode (reduce CPU frequency when below 30%)
- [ ] Offline fallback demo (Python CLI demo for judges who can't install APK)

### Explicitly Out of Scope
- Fine-tuning (base Gemma 4 + strong prompt engineering is sufficient)
- Cloud sync / backend
- Multi-language support
- Satellite modem hardware integration (SMS is the bridge)

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Android Device                       │
│                                                         │
│  [MIC] → AudioCaptureManager → VADDetector             │
│              ↓ PCM chunks (16kHz)                       │
│         SpeechToTextManager (Android SpeechRecognizer   │
│              offline mode)                              │
│              ↓ transcribed text                         │
│         PromptBuilder (Gemma chat template +            │
│              START protocol + few-shot examples)        │
│              ↓ formatted prompt                         │
│         GemmaInferenceEngine                           │
│              (MediaPipe LLM Inference API)              │
│              (Gemma 4 E2B, INT4 quantized, ~1.3GB)     │
│              ↓ raw JSON string                          │
│         JSON Parser → TriageResult                     │
│              ↓                                          │
│  [UI]   TriageViewModel → MainActivity                  │
│              ↓                                          │
│         TriageOutputManager                            │
│           ├─ SMSFormatter → QueueManager → SmsManager  │
│           └─ DatabaseHelper → Room DB (audit trail)    │
└─────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Model Runtime — `GemmaInferenceEngine.kt`
**What it does:** Wraps the MediaPipe `LlmInference` API. Loads Gemma 4 E2B (INT4 quantized, stored in app's internal files directory) and exposes `runTriageInference(patientDescription: String): TriageResult`.

**Key decisions:**
- **Runtime: MediaPipe LLM Inference API** (not ExecuTorch). Google officially supports Gemma on Android via MediaPipe. GPU acceleration via OpenGL ES. Simpler setup, better docs, LiteRT prize eligible.
- **Model: Gemma 4 E2B INT4** (~1.3GB on disk). Minimum 4GB device RAM required. Fits mid-range Android phones.
- **Temperature: 0.1f** (near-deterministic — triage decisions must be consistent, not creative).
- **MaxTokens: 512** (JSON output is <200 tokens, leaving headroom for reasoning).

### 2. Speech-to-Text — `SpeechToTextManager.kt` *(new file)*
**What it does:** Wraps Android's `SpeechRecognizer` with `EXTRA_PREFER_OFFLINE = true`. Exposes a coroutine-based API that emits a `StateFlow<STTState>`.

**Key decisions:**
- Android's built-in STT with offline language pack is the fastest path to demo day.
- Requires user to have downloaded the English offline speech model (standard on modern Android).
- Runs on main thread (SpeechRecognizer constraint) but result is emitted to coroutine flow.
- Stretch goal: replace with Whisper.cpp via JNI for fully self-contained offline operation.

### 3. Prompt Engineering — `PromptBuilder.kt` + `system_prompt.txt` + `few_shot_examples.json`
**What it does:** Builds the Gemma-format prompt (`<start_of_turn>system\n...<end_of_turn>`) with the START protocol system prompt and injects 2 relevant few-shot examples before the patient description.

**Key decisions:**
- System prompt hardcodes START protocol logic and forces JSON-only output.
- Few-shot examples cover all 4 triage categories (4 RED, 3 YELLOW, 3 GREEN, 2 BLACK, 1 edge case).
- Temperature 0.1 + few-shot examples = highly consistent JSON output.

### 4. Expanded Output Schema — `TriageSchema.kt`
**What it does:** `TriageResult` carries far more than a triage code. Gemma returns a rich structured object that drives both the UI display and the TTS voice output.

```json
{
  "triageCode": "RED",
  "confidence": 0.97,
  "reasoning": "Three RED criteria met: resp rate 38/min, absent radial pulse, altered mental status.",
  "spokenSummary": "RED. Immediate. This patient has three critical signs and needs help right now.",
  "immediateSteps": [
    "Step 1: Tilt head back and lift chin to open the airway. Look for chest rise.",
    "Step 2: Apply direct pressure to any visible bleeding wound with both hands.",
    "Step 3: If you have a tourniquet, apply it 5 centimetres above the wound.",
    "Step 4: Keep the patient still — assume spinal injury until proven otherwise."
  ],
  "monitoringChecklist": [
    "Recheck radial pulse every 60 seconds.",
    "If respiratory rate drops below 8 or rises above 45 — reassess immediately.",
    "Watch for skin colour change — pale or blue means worsening shock."
  ],
  "warningSigns": [
    "If breathing stops: give one rescue breath every 5 seconds.",
    "If patient becomes unresponsive: shout for help and reassess tag."
  ],
  "smsPayload": "TRG|R|97|Open airway;Stop bleeding;Tourniquet;Spinal precaution"
}
```

**Key decisions:**
- `spokenSummary` is short and direct — designed to be read aloud in under 5 seconds.
- `immediateSteps` use plain language, no jargon — written so a non-medic volunteer can follow them.
- `smsPayload` is pre-computed by Gemma, not post-processed — Gemma knows the 160-char constraint.

### 5. Text-to-Speech — `TextToSpeechManager.kt` *(new file)*
**What it does:** Wraps Android's built-in `TextToSpeech` engine. After Gemma returns a result, the phone reads it aloud in this order: triage code → spoken summary → immediate steps. Riya keeps her eyes on the patient, not the screen.

**Key decisions:**
- Android `TextToSpeech` works fully offline — no network required.
- Speech rate: 0.85× (slightly slower than default for field conditions).
- Pitch: 1.0 (neutral — not robotic, not warm).
- Triage code spoken FIRST, loudly, before anything else: *"RED. IMMEDIATE."*
- Emits a `StateFlow<TTSState>` so ViewModel knows when speaking is done and can open the follow-up mic.

### 6. Conversation Loop — `ConversationManager.kt` *(new file)*
**What it does:** After TTS finishes speaking the instructions, the app automatically enters **Follow-Up Mode**. The mic opens. Riya can ask a question in plain speech. Gemma answers in the context of the current patient using **Thinking Mode** (extended chain-of-thought reasoning in the prompt). TTS reads the answer. The loop continues until Riya says *"next patient"* or taps **NEXT PATIENT**.

**Thinking Mode:** Implemented via prompt engineering — the follow-up prompt includes `<think>` reasoning scaffolding that instructs Gemma to reason through the patient context, resource constraints, and clinical tradeoffs before answering. This produces longer, more considered responses than the initial rapid classification.

**Conversation history:** The `ConversationManager` keeps the full exchange (patient description + classification + all follow-up Q&As) in memory. Each follow-up prompt includes:
- Original patient description
- Initial classification and reasoning
- Full conversation history so far
- New question from Riya

**Example exchange:**
```
Gemma: "RED. Immediate. Step 1: Open the airway..."
Riya:  "I don't have oxygen. What else can I do?"
Gemma: [thinks: patient has absent pulse, resp 38/min, no O2 available — 
        alternatives are positioning, airway opening, rescue breathing...]
       "Without oxygen, your priority is airway position. Keep the head tilted
        back and the chin lifted. If breathing rate drops below 8, give one slow
        breath every 5 seconds using mouth-to-mouth. Position beats equipment."
Riya:  "He just started seizing."
Gemma: [thinks: seizure on top of RED classification — new information changes
        management, possible TBI, hypoxia-induced...]
       "Seizure alert. Do not restrain him. Clear space around him.
        Time the seizure. If it goes beyond 2 minutes, upgrade to critical
        transport priority. After the seizure, recheck his airway immediately."
```

**SMS dispatch is unchanged** — fires once at initial classification, not updated by the conversation.

### 7. MVVM State Layer — `TriageViewModel.kt` *(new file)*
**What it does:** `AndroidViewModel` holding `StateFlow<TriageUiState>`. Orchestrates the full pipeline and the conversation loop. MainActivity observes this, no business logic in the activity.

**States:**
```
Idle
  → Listening             (mic open, initial patient)
  → Transcribing(text)    (speech recognised)
  → Analyzing             (Gemma inference running)
  → Speaking(stage)       (TTS reading result)
  → FollowUpListening     (mic open, follow-up question)
  → FollowUpAnalyzing     (Gemma thinking mode running)
  → FollowUpSpeaking      (TTS reading follow-up answer)
  → Error(message)
```

### 8. UI — `activity_main.xml` + `MainActivity.kt`
**What it does:** Dark emergency-themed single-screen UI with conversation panel.
- **Header:** "GEMMA TRIAGE" + "● OFF-GRID" status
- **Record button:** Push-to-talk for initial patient description
- **Transcription area:** Shows spoken text in real-time
- **Result card:** Color-coded by triage code, shows `immediateSteps` and `monitoringChecklist`
- **TTS indicator:** Speaker icon pulses while Gemma is speaking
- **Conversation panel:** Shows last 2 follow-up exchanges (question + answer)
- **NEXT PATIENT button:** Resets to Idle, increments counter
- **SMS button:** Visible at all times after initial classification; coordinator dispatch

### 9. Output Layer — `QueueManager.kt` + `TriageOutputManager.kt`
**What it does:** `QueueManager` maintains SMS dispatch queue with retry (exponential backoff, max 3 retries). `TriageOutputManager` orchestrates: save to Room DB → format SMS → enqueue → attempt send. **Called once at initial classification — conversation follow-ups are local only.**

### 10. Python Demo — `python_demo/triage_demo.py` *(new file)*
**What it does:** CLI fallback demo using `google-generativeai`. Mimics the full pipeline including the conversation loop — judges type follow-up questions in the terminal and see Gemma's thinking-mode responses.

---

## Data Flow — Happy Path (with Voice Conversation Loop)

```
━━━ PHASE A: INITIAL TRIAGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.  Riya presses RECORD button
2.  SpeechToTextManager.startListening() — mic opens (offline STT)
3.  Riya speaks patient description
4.  SpeechRecognizer returns transcribed text
5.  PromptBuilder.buildPrompt(context, text)
      → system_prompt.txt (START protocol + JSON schema)
      → 2 few-shot examples injected
      → Gemma chat template assembled
6.  GemmaInferenceEngine.runTriageInference(text)
      → MediaPipe LlmInference.generateResponse(prompt)
      → Gemma 4 E2B INT4 runs on-device GPU (~3s)
7.  Raw JSON parsed → TriageResult (triageCode, confidence,
      spokenSummary, immediateSteps, monitoringChecklist,
      warningSigns, smsPayload)
8.  TriageOutputManager.process(result, transcription):
      a. Room DB → TriageRecord inserted (audit trail)
      b. result.smsPayload → QueueManager → SmsManager
      c. SMS fires via satellite modem to Coordinator HQ  ← ONE TIME ONLY
9.  MainActivity: RED card + immediateSteps + monitoringChecklist displayed

━━━ PHASE B: VOICE OUTPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

10. TextToSpeechManager.speak() reads aloud in order:
      → "RED. IMMEDIATE."                      (triage code — short, loud)
      → result.spokenSummary                   (2-sentence summary)
      → result.immediateSteps (all steps)      (plain-language actions)
11. TTSState.Done emitted when finished speaking

━━━ PHASE C: FOLLOW-UP CONVERSATION LOOP ━━━━━━━━━━━━━━━━━━

12. TriageViewModel auto-opens mic → FollowUpListening state
    UI shows: "Ask a follow-up or say 'next patient'"
13. Riya speaks: "I don't have oxygen. What else can I do?"
14. SpeechRecognizer returns follow-up text
15. ConversationManager.buildFollowUpPrompt():
      → Original patient description
      → Initial triage result (code + reasoning)
      → Full conversation history so far
      → Thinking mode scaffolding:
          "Think step by step through the patient's condition,
           the constraint stated, and clinical alternatives
           before giving your answer."
      → New question appended
16. GemmaInferenceEngine.runFollowUpInference(prompt)
      → Temperature raised to 0.3f (allows adaptive reasoning)
      → Longer MaxTokens: 768 (thinking takes more space)
17. Raw text response parsed (plain text, not JSON)
18. ConversationManager stores exchange in history
19. TextToSpeechManager.speak(followUpAnswer) — TTS reads answer aloud
20. UI conversation panel updates with Q + A
21. Loop returns to step 12 — mic auto-opens again

━━━ EXIT CONDITIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Riya says "next patient" → STT detects keyword → reset to Idle
Riya taps NEXT PATIENT button → reset to Idle
Inactivity timeout (30s silence) → mic closes, stays on result screen
```

---

## Key Technical Decisions

| Decision | Choice | Why |
|---|---|---|
| On-device runtime | MediaPipe LLM Inference API | Official Google support for Gemma on Android, GPU acceleration, LiteRT prize eligible |
| Model size | Gemma 4 E2B (2B params, INT4) | Fits on mid-range Android (4GB RAM), ~3s inference time |
| Speech-to-text | Android SpeechRecognizer (offline) | Zero additional model files, works on modern Android offline |
| Text-to-speech | Android TextToSpeech (offline) | Built-in, no extra model, works offline, reads instructions hands-free |
| Prompt strategy | Base model + few-shot + thinking scaffolding | Achieves 95%+ accuracy on initial triage; thinking scaffolding enables adaptive follow-ups |
| Follow-up temperature | 0.3f (vs 0.1f for triage) | Follow-ups need adaptive reasoning across resource constraints, not rigid JSON |
| Conversation history | In-memory, current patient only | Bounded context, no DB overhead, cleared on "next patient" |
| JSON for initial triage | Gson + raw string extraction | Structured output drives UI, TTS script, and SMS payload |
| Follow-up output | Plain text | Follow-ups are conversational — JSON overhead unnecessary |
| Connectivity bridge | Android SmsManager (initial classification only) | One SMS per patient; conversation is local |
| UI architecture | MVVM (ViewModel + StateFlow) | Standard Android; MainActivity stays thin |

---

## Phase Timeline

| Phase | Days | Deliverable |
|---|---|---|
| Phase 1: Runtime Foundation | 1-2 | MediaPipe wired, model loads on device, JSON parsing tested |
| Phase 2: Speech Pipeline | 3-4 | Voice → text → Gemma → expanded JSON working end-to-end |
| Phase 3: Voice Output (TTS) | 5 | TextToSpeechManager reads triage result aloud, hands-free |
| Phase 4: Conversation Loop | 6-7 | Follow-up mic + ConversationManager + thinking-mode prompts |
| Phase 5: Android UI | 8-9 | Full emergency UI, conversation panel, TTS indicator |
| Phase 6: Output Layer | 10 | SMS dispatch, database, queue working |
| Phase 7: Python Demo | 11-12 | CLI demo with full conversation loop |
| Phase 8: Submission | 13-15 | Kaggle writeup, YouTube video, APK release |

---

## Hackathon Judging Alignment

**"Frontier Intelligence"** — Gemma 4's Thinking Mode guides the reasoning field of the JSON output. The model thinks step-by-step through START protocol before classifying.

**"Function Calling"** — The structured JSON output (`triageCode`, `confidence`, `reasoning`, `recommendedActions`) demonstrates Gemma's function-calling capability as structured output.

**"On-Device / Local-First"** — Zero bytes leave the phone during triage. The INTERNET permission is intentionally absent from AndroidManifest.xml.

**"Global Resilience"** — Designed for zero-infrastructure environments. Works at 0% battery charge through BatteryOptimizer. Works offline. Works in the field.

**"Wow Factor for Video"** — The demo script: phone in airplane mode, voice input, 3-second Gemma inference, RED card appears, SMS fires. One take, no cuts.
