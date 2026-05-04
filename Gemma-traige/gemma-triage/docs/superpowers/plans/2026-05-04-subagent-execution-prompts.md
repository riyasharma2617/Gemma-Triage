# Gemma Triage — Subagent Execution Prompts
**How to use:** Copy the prompt for the phase you want to execute and paste it into a new Claude Code session. Each prompt is self-contained — the agent needs no memory of previous sessions.

---

## Before You Start Any Phase

Read these files first. They contain everything you need:
- `CLAUDE.md` — recurring rules (feature docs, TDD, commit format, build commands)
- `docs/superpowers/specs/2026-05-04-gemma-triage-design.md` — full design spec
- `docs/superpowers/plans/2026-05-04-gemma-triage-plan.md` — full implementation plan with code

---

## Phase 1 Prompt — Runtime Foundation
**Paste this into a new session to execute Phase 1.**

```
You are implementing Phase 1 of the Gemma Triage Android app — a hackathon project
(deadline May 18 2026) that does offline disaster triage using Gemma 4 on-device.

START by reading these files in order:
1. CLAUDE.md                                                     (recurring rules)
2. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md        (full plan with code)
   Read: Phase 1 (Tasks 1–4), File Map section

Then invoke the `superpowers:executing-plans` skill and execute Tasks 1–4 from the plan:

TASK 1 — build.gradle
  Replace the dependencies block with the MediaPipe + Gson + ViewModel + Room deps shown
  in the plan. Add packagingOptions block. Sync gradle.
  Commit: "chore: switch to MediaPipe tasks-genai + add ViewModel and Gson deps"

TASK 2 — system_prompt.txt + few_shot_examples.json
  Write the full START protocol system prompt to assets/prompts/system_prompt.txt
  Write all 13 few-shot examples to assets/prompts/few_shot_examples.json
  Use the exact content shown in the plan (Task 2 has the complete text).
  Commit: "feat: add START protocol system prompt and 13 few-shot triage examples"

TASK 3 — GemmaInferenceEngine.kt + TriageSchema.kt + InferenceTest.kt
  Replace TriageSchema.kt with the expanded schema (triageCode, confidence, reasoning,
  spokenSummary, immediateSteps, monitoringChecklist, warningSigns, smsPayload fields).
  Write the 4 unit tests in InferenceTest.kt first. Run — confirm they FAIL.
  Rewrite GemmaInferenceEngine.kt with MediaPipe LlmInference + parseTriageResultFromJson
  companion object. Run tests — confirm they PASS.
  Commit: "feat: GemmaInferenceEngine with MediaPipe LlmInference + expanded JSON parsing"

TASK 4 — PromptBuilder.kt
  Rewrite PromptBuilder.kt with context-aware buildPrompt (loads system_prompt.txt +
  samples 2 few-shot examples) and a no-context overload for unit tests.
  Update GemmaInferenceEngine.runTriageInference to use context-aware overload.
  Run tests — all must PASS.
  Commit: "feat: PromptBuilder injects few-shot examples from assets at runtime"

AFTER ALL TASKS:
1. Run: ./gradlew :app:testDebugUnitTest  (all pass)
2. Run: ./gradlew :app:compileDebugKotlin (BUILD SUCCESSFUL)
3. Create: docs/features/phase-1-runtime-foundation.md
   (what was built, key files, how to test, limitations)
4. Invoke superpowers:requesting-code-review skill
5. Commit the feature doc: "docs: add Phase 1 runtime foundation feature doc"

SUCCESS CRITERIA:
- 4+ unit tests pass in InferenceTest.kt
- parseTriageResultFromJson handles clean JSON, preamble text, malformed output
- PromptBuilder loads real assets (verify in logcat on device)
- Build compiles clean
- No INTERNET permission in AndroidManifest.xml
```

---

## Phase 2 Prompt — Speech Pipeline
**Paste this into a new session AFTER Phase 1 is complete.**

```
You are implementing Phase 2 of the Gemma Triage Android app — offline disaster triage
using Gemma 4 on Android (hackathon deadline May 18 2026).

Phase 1 is already complete: MediaPipe wired, GemmaInferenceEngine working, expanded
TriageSchema, system_prompt.txt and few_shot_examples.json written.

START by reading:
1. CLAUDE.md                                                     (recurring rules)
2. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md        (read Phase 2: Tasks 5-6)
3. android/app/src/main/java/com/gemma/triage/audio/AudioCaptureManager.kt
   (understand existing audio layer before building on top of it)

Then invoke `superpowers:executing-plans` and execute Tasks 5–6:

TASK 5 — SpeechToTextManager.kt
  Create: android/app/src/main/java/com/gemma/triage/audio/SpeechToTextManager.kt
  Wraps Android SpeechRecognizer with EXTRA_PREFER_OFFLINE=true.
  Exposes StateFlow<STTState> (Idle, Listening, Result(text), Error(code, message)).
  Includes mapSpeechError() for human-readable error messages.
  Manual verification: add temp startListening() call in MainActivity, speak patient
  description, verify logcat shows STTState.Result(text="..."), remove temp call.
  Commit: "feat: add SpeechToTextManager with offline STT and STTState flow"

TASK 6 — TriageViewModel.kt + TriageUiState.kt (initial version)
  Create: android/app/src/main/java/com/gemma/triage/viewmodel/TriageUiState.kt
  States: Idle, Listening, Transcribing(text), Analyzing, ResultReady(result, transcription),
          Speaking(stage), FollowUpListening, FollowUpAnalyzing, FollowUpSpeaking(q, a), Error(msg)
  Create: android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt
  AndroidViewModel wiring STT → inference → output. Use the full version from the plan
  (Task 11 in Phase 3c has the complete TriageViewModel — implement that full version now,
  not the earlier partial version, since it includes TTS and conversation loop).
  Build: ./gradlew :app:compileDebugKotlin — must succeed.
  Commit: "feat: add TriageViewModel + TriageUiState with full pipeline states"

AFTER ALL TASKS:
1. Run: ./gradlew :app:testDebugUnitTest  (all pass)
2. Run: ./gradlew :app:compileDebugKotlin (BUILD SUCCESSFUL)
3. Create: docs/features/phase-2-speech-pipeline.md
4. Invoke superpowers:requesting-code-review skill
5. Commit the feature doc: "docs: add Phase 2 speech pipeline feature doc"

SUCCESS CRITERIA:
- SpeechToTextManager compiles and emits STTState correctly
- EXTRA_PREFER_OFFLINE=true present in RecognizerIntent
- TriageViewModel compiles with all 10 UI states
- No INTERNET permission in AndroidManifest.xml
```

---

## Phase 3 Prompt — Voice Output (TTS)
**Paste this into a new session AFTER Phase 2 is complete.**

```
You are implementing Phase 3 of the Gemma Triage Android app — adding text-to-speech
so Riya (the field medic) hears triage instructions aloud without looking at the screen.
Hackathon deadline: May 18 2026.

Phases 1 and 2 are done: MediaPipe inference, SpeechToTextManager, TriageViewModel all
compile and work.

START by reading:
1. CLAUDE.md
2. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md        (read Phase 3b: Task 9)
3. android/app/src/main/java/com/gemma/triage/inference/TriageSchema.kt
   (understand the TriageResult fields: spokenSummary, immediateSteps, etc.)

Then invoke `superpowers:executing-plans` and execute Task 9:

TASK 9 — TextToSpeechManager.kt
  Create: android/app/src/main/java/com/gemma/triage/audio/TextToSpeechManager.kt
  Implements TextToSpeech.OnInitListener.
  speakTriageResult(result): speaks in order —
    1. "${result.triageCode.name}. ${label}."   utteranceId="CODE"
    2. result.spokenSummary                      utteranceId="SUMMARY"
    3. each immediateStep                        last one gets utteranceId="DONE"
  speakFollowUpAnswer(answer): speaks answer, utteranceId="DONE"
  UtteranceProgressListener: emits TTSState.Done when utteranceId == "DONE"
  Speech rate: 0.85f, pitch: 1.0f, locale: Locale.US
  Exposes StateFlow<TTSState> (Idle, Speaking(stage), Done, Error(message))

  Write unit test (from plan Task 9 Step 2) — verify DONE is emitted on last step.
  Run test — PASS.
  Commit: "feat: add TextToSpeechManager — reads triage result aloud, emits Done on finish"

  Manual test on device:
  - Temporarily call ttsManager.speak("RED. Immediate.", "DONE") in MainActivity.onCreate
  - Install APK, verify phone speaks the text
  - Remove temp call

AFTER TASK:
1. Run: ./gradlew :app:testDebugUnitTest  (all pass)
2. Run: ./gradlew :app:compileDebugKotlin (BUILD SUCCESSFUL)
3. Create: docs/features/phase-3-text-to-speech.md
4. Invoke superpowers:requesting-code-review skill
5. Commit doc: "docs: add Phase 3 TTS feature doc"

SUCCESS CRITERIA:
- TextToSpeechManager compiles, uses offline TextToSpeech engine
- speakTriageResult speaks all 3 stages (code, summary, steps)
- TTSState.Done emitted exactly when last utterance finishes
- No network calls made by TTS (Android built-in TTS is offline)
```

---

## Phase 4 Prompt — Conversation Loop
**Paste this into a new session AFTER Phase 3 is complete.**

```
You are implementing Phase 4 of the Gemma Triage Android app — the voice follow-up
conversation loop. After Riya hears the triage instructions, she can speak follow-up
questions ("I don't have oxygen", "he started seizing") and Gemma answers using
thinking-mode reasoning. Hackathon deadline: May 18 2026.

Phases 1–3 done: inference, STT, TTS all working.

START by reading:
1. CLAUDE.md
2. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md  (read Phase 3c: Tasks 10-12)
3. docs/riya-pipeline-walkthrough.md                        (read Phase C section)
4. android/app/src/main/java/com/gemma/triage/inference/GemmaInferenceEngine.kt
5. android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt

Then invoke `superpowers:executing-plans` and execute Tasks 10–12:

TASK 10 — ConversationManager.kt
  Create: android/app/src/main/java/com/gemma/triage/inference/ConversationManager.kt
  Holds: patientDescription, initialResult, history (List<ConversationTurn>)
  startNewPatient(description, result) — clears and initialises
  addTurn(role, text) — appends to history
  buildFollowUpPrompt(question) — assembles full prompt:
    system: thinking-mode instructions (step-by-step reasoning, plain language, max 4 sentences)
    patient context turn (description + classification)
    full history so far
    new question
  isNextPatientCommand(text) — detects "next patient", "new patient", "next case", "done", "next"
  clear() — resets everything

  Write unit tests (from plan Task 10 Step 2):
    - isNextPatientCommand detects exit phrases correctly
    - buildFollowUpPrompt includes patient context and conversation history
  Run — FAIL. Implement. Run — PASS.
  Commit: "feat: add ConversationManager with thinking-mode prompt builder and next-patient detection"

TASK 11 — Update TriageViewModel + TriageUiState + GemmaInferenceEngine
  Replace TriageUiState.kt with the full 10-state version (from plan Task 11 Step 1).
  Replace TriageViewModel.kt with the full version (plan Task 11 Step 2) that:
    - observes TTSState.Done → auto-opens follow-up mic
    - routes STT results to runInitialInference or runFollowUpInference
    - detects "next patient" keyword via ConversationManager.isNextPatientCommand
    - resets conversation on resetToNextPatient()
  Add runFollowUpInference(prompt) to GemmaInferenceEngine (plan Task 11 Step 3):
    - strips <thinking>...</thinking> block from output before returning
    - uses existing llmInference instance (no temp change possible in MediaPipe API —
      note this as known limitation in feature doc)
  Build: ./gradlew :app:compileDebugKotlin — must succeed.
  Run all tests: ./gradlew :app:testDebugUnitTest — all pass.
  Commit: "feat: wire TTS→mic follow-up loop in TriageViewModel; add runFollowUpInference"

TASK 12 — Update MainActivity + activity_main.xml for conversation UI
  Add to activity_main.xml: TTS indicator (speaker icon + label), conversation panel
  (question + answer card), follow-up prompt label, NEXT PATIENT button.
  Update MainActivity.observeViewModel() to handle all 10 states including
  showSpeaking(), showFollowUpListening(), showFollowUpResult().
  Wire btnNextPatient.setOnClickListener → viewModel.resetToNextPatient()
  Install and manual test the full loop:
    Speak RED patient → see card → hear TTS → mic reopens → ask follow-up → hear answer
    → ask second follow-up → say "next patient" → verify reset
  Commit: "feat: add conversation panel + TTS indicator + follow-up UI to MainActivity"

AFTER ALL TASKS:
1. Run: ./gradlew :app:testDebugUnitTest  (all pass)
2. Run: ./gradlew :app:assembleDebug      (BUILD SUCCESSFUL)
3. Create: docs/features/phase-4-conversation-loop.md
4. Invoke superpowers:requesting-code-review skill
5. Commit doc: "docs: add Phase 4 conversation loop feature doc"

SUCCESS CRITERIA:
- ConversationManager unit tests pass
- Full voice loop works: triage → TTS → mic auto-opens → follow-up → TTS → loop
- "next patient" keyword resets cleanly
- Conversation history clears on each new patient
- SMS is NOT fired during follow-up exchanges
- No INTERNET permission in AndroidManifest.xml
```

---

## Phase 5 Prompt — Output Layer (SMS + Database)
**Paste this into a new session AFTER Phase 4 is complete.**

```
You are implementing Phase 5 of the Gemma Triage Android app — the output layer:
SMS dispatch to the coordination center and Room database audit trail.
Hackathon deadline: May 18 2026.

Phases 1–4 done: inference, STT, TTS, conversation loop all working. The
TriageOutputManager.process() stub is called from TriageViewModel but is empty.

START by reading:
1. CLAUDE.md
2. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md  (read Phase 4: Tasks 9-10)
   NOTE: In the plan these are numbered Task 9 and Task 10 under "Phase 4: Output Layer"
3. android/app/src/main/java/com/gemma/triage/storage/DatabaseHelper.kt  (Room already set up)
4. android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt
5. android/app/src/main/java/com/gemma/triage/output/SMSFormatter.kt     (already exists)

Then invoke `superpowers:executing-plans` and execute the Output Layer tasks:

TASK A — Implement QueueManager.kt
  File: android/app/src/main/java/com/gemma/triage/output/QueueManager.kt
  PendingSMS data class (destination, message, retries: Int = 0)
  QueueManager(context):
    COORDINATOR_NUMBER = "+911234567890"  (placeholder — note in doc)
    MAX_RETRIES = 3
    enqueue(message) → adds to ConcurrentLinkedQueue → calls attemptSend()
    attemptSend() → SmsManager.getDefault().sendTextMessage() → on failure: retries++
    retryPending() suspend fun with exponential backoff
  Write unit test: SMSFormatter produces ≤160 chars and contains "|R|" for RED result.
  Run — PASS.
  Commit: "feat: implement QueueManager with retry logic for SMS dispatch"

TASK B — Implement TriageOutputManager.kt
  File: android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt
  process(result: TriageResult, transcription: String) on Dispatchers.IO:
    1. db.triageDao().insert(TriageRecord(
         timestamp = System.currentTimeMillis(),
         patientDescription = transcription,
         triageCode = result.triageCode.name,
         confidence = result.confidence,
         isTransmitted = false
       ))
    2. queueManager.enqueue(result.smsPayload)
       NOTE: use result.smsPayload (pre-computed by Gemma) — NOT SMSFormatter.
       SMSFormatter is the fallback if smsPayload is blank.
  Manual test: complete one triage cycle, check Room DB via Android Studio
  App Inspection → Database → triage_records (verify 1 row inserted).
  Commit: "feat: implement TriageOutputManager — Room DB insert + SMS dispatch via smsPayload"

AFTER ALL TASKS:
1. Run: ./gradlew :app:testDebugUnitTest  (all pass)
2. Run: ./gradlew :app:assembleDebug      (BUILD SUCCESSFUL)
3. Verify: AndroidManifest.xml has SEND_SMS but NOT INTERNET permission
4. Create: docs/features/phase-5-output-layer.md
5. Invoke superpowers:requesting-code-review skill
6. Commit doc: "docs: add Phase 5 output layer feature doc"

SUCCESS CRITERIA:
- Every triage session inserts a TriageRecord into Room DB
- SMS dispatch uses result.smsPayload (≤160 chars, pre-computed by Gemma)
- QueueManager retries up to 3× on send failure
- SMS fires exactly once per patient (not during follow-up conversation)
- No INTERNET permission
```

---

## Phase 6 Prompt — Python Demo (Judge Fallback)
**Paste this into a new session AFTER Phase 5 is complete.**

```
You are implementing Phase 6 of the Gemma Triage Android app — a Python CLI demo
that mimics the full Android pipeline including the voice conversation loop.
This is the fallback for judges who can't install an Android APK.
Hackathon deadline: May 18 2026.

Phases 1–5 done: the Android app is fully functional.

START by reading:
1. CLAUDE.md
2. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md  (read Phase 5: Tasks 11-12)
3. docs/riya-pipeline-walkthrough.md                        (understand the full flow)
4. android/app/src/main/assets/prompts/system_prompt.txt    (copy the exact prompt)

Then invoke `superpowers:executing-plans` and execute:

TASK A — python_demo/requirements.txt
  Contents:
    google-generativeai>=0.8.0
    rich>=13.7.0
  Commit: "chore: add Python demo requirements"

TASK B — python_demo/triage_demo.py (full conversation loop version)
  Build on the plan's Task 12 demo but ADD the full conversation loop:

  System prompt: copy exactly from android/app/src/main/assets/prompts/system_prompt.txt
  BUT also add the expanded JSON schema fields to the prompt (spokenSummary, immediateSteps,
  monitoringChecklist, warningSigns, smsPayload).

  Flow for each patient:
  1. User types patient description (simulates voice input)
  2. Call Gemma with system prompt + 2 random few-shot examples + patient description
     temperature=0.1, max_output_tokens=768
  3. Parse expanded JSON response
  4. Display rich result card (RED/YELLOW/GREEN/BLACK color-coded)
     Show: triage code, confidence, reasoning, immediateSteps (numbered), monitoringChecklist
  5. Print: "SMS that would fire: <smsPayload>"
  6. Enter follow-up loop:
     - Prompt: "Follow-up question (or 'next patient' / 'quit'): "
     - Build thinking-mode follow-up prompt with:
         patient context + initial result + conversation history + new question
     - Call Gemma at temperature=0.3, max_output_tokens=768
     - Strip any <thinking>...</thinking> from response
     - Display answer, add to history
     - Loop until user types "next patient" or "quit"
  7. On "next patient": clear history, increment counter, loop back

  configure_gemma() function:
    Check GEMINI_API_KEY env var
    Use model_name="gemma-3-27b-it"  # update to Gemma 4 name when available on API

  Test with:
    Patient: "Male, 40, breathing 38/min, absent radial pulse, not following commands"
    Expected: RED, confidence >0.9, 4+ immediateSteps
    Follow-up: "I don't have oxygen" — verify contextual answer
    Follow-up: "next patient" — verify reset

  Commit: "feat: Python CLI demo with full conversation loop and expanded JSON output"

AFTER ALL TASKS:
1. Test: cd python_demo && pip install -r requirements.txt && GEMINI_API_KEY=<key> python triage_demo.py
2. Create: docs/features/phase-6-python-demo.md
3. Invoke superpowers:requesting-code-review skill
4. Commit doc: "docs: add Phase 6 Python demo feature doc"

SUCCESS CRITERIA:
- Demo runs from cold start with just GEMINI_API_KEY set
- Full expanded JSON parsed and displayed
- Follow-up conversation loop works for 2+ exchanges
- "next patient" resets cleanly
- SMS payload printed for each patient
```

---

## Phase 7 Prompt — Evaluation Harness
**Paste this into a new session AFTER Phase 6 is complete.**

```
You are implementing Phase 7 of the Gemma Triage Android app — an evaluation harness
that tests the Gemma prompt pipeline against known cases and reports accuracy.
This is needed for the Kaggle writeup ("Results" section).
Hackathon deadline: May 18 2026.

START by reading:
1. CLAUDE.md
2. android/app/src/main/assets/prompts/few_shot_examples.json  (13 test cases to evaluate)
3. model/evaluation/test_cases.json                             (existing test cases if any)
4. model/evaluation/evaluate.py                                 (existing stub)

Then implement:

TASK A — Expand model/evaluation/test_cases.json
  Add 20 test cases (5 per triage category: RED, YELLOW, GREEN, BLACK).
  Each case: { "input": "...", "expected": "RED|YELLOW|GREEN|BLACK" }
  Make cases realistic — varied symptoms, ages, mechanisms.
  Do NOT reuse the 13 cases already in few_shot_examples.json.
  Commit: "test: add 20 evaluation test cases covering all 4 triage categories"

TASK B — Implement model/evaluation/evaluate.py
  Reads test_cases.json, calls Gemma via google-generativeai (same config as python_demo),
  compares triageCode to expected, reports:
    - Per-category accuracy (RED: 5/5, YELLOW: 4/5, etc.)
    - Overall accuracy (e.g., 18/20 = 90%)
    - Any misclassified cases (input + expected + got)
    - Average response time per inference
  Usage: GEMINI_API_KEY=<key> python model/evaluation/evaluate.py
  Commit: "feat: implement evaluation harness with per-category accuracy reporting"

AFTER ALL TASKS:
1. Run evaluation: GEMINI_API_KEY=<key> python model/evaluation/evaluate.py
2. Record results in docs/features/phase-7-evaluation.md
   Include: accuracy numbers, any patterns in misclassifications, inference time
3. Invoke superpowers:requesting-code-review skill
4. Commit doc: "docs: add Phase 7 evaluation results and harness feature doc"

SUCCESS CRITERIA:
- Evaluation runs against all 20 cases without crashing
- Overall accuracy ≥ 85% (target for Kaggle writeup)
- Results table in the feature doc (for copy-paste into Kaggle writeup)
```

---

## Phase 8 Prompt — Submission Prep
**Paste this into a new session AFTER Phases 1–7 are complete.**

```
You are preparing the final submission for the Gemma Triage hackathon entry.
Deadline: May 18 2026 (submit by May 19 5:29 AM GMT+5:30).

All features are implemented. This phase is about polish, documentation, and submission.

START by reading:
1. CLAUDE.md
2. docs/superpowers/specs/2026-05-04-gemma-triage-design.md  (spec for writeup content)
3. docs/riya-pipeline-walkthrough.md                          (for writeup narrative)
4. docs/features/                                              (all feature docs for results)
5. model/evaluation/evaluate.py output                        (for accuracy numbers)

Then execute in order:

TASK A — Release APK
  In android/app/build.gradle, set versionCode=1, versionName="1.0.0"
  Run: ./gradlew :app:testDebugUnitTest  (all must pass before release)
  Run: ./gradlew :app:assembleRelease
  Output: android/app/build/outputs/apk/release/app-release-unsigned.apk
  Commit: "chore: bump to v1.0.0 for submission release"

TASK B — Update README.md
  The README is at Gemma-traige/gemma-triage/README.md (currently empty).
  Write a proper README with:
    - Project title + one-line description
    - The "Operation Zero-Signal" storyline (from spec)
    - Features list (offline, voice, TTS, conversation loop, SMS)
    - Architecture diagram (ASCII, from spec)
    - Setup instructions (run setup_model.py, install APK)
    - Python demo instructions
    - Tech stack
    - Prize tracks targeted
    - Demo video link (placeholder: [YouTube link])
  Commit: "docs: write complete README for hackathon submission"

TASK C — Write docs/kaggle_writeup.md
  Fill in the full Kaggle writeup (≤1500 words). Sections:
    The Problem (150 words): earthquake scenario, no connectivity, medic memory limits
    The Solution (200 words): Gemma 4 on-device, full pipeline, voice in/out, SMS
    Technical Implementation (500 words):
      - Architecture overview
      - MediaPipe LlmInference API + Gemma 4 E2B INT4
      - Expanded prompt engineering (START protocol + few-shot + thinking mode)
      - TextToSpeechManager (hands-free instructions)
      - ConversationManager (adaptive follow-up loop)
      - SMSFormatter (160-char compressed dispatch)
    Results (200 words): accuracy from evaluation, inference time, demo link
    Why Gemma 4 (150 words): on-device capability, structured output, reasoning quality
    Prize Alignment (150 words): Global Resilience + LiteRT tracks
    Future Work (50 words): Whisper STT, multilingual, satellite modem
  Word count MUST be ≤1500. Check with: wc -w docs/kaggle_writeup.md
  Commit: "docs: write Kaggle submission writeup (≤1500 words)"

TASK D — Video Script (docs/video_script.md)
  Write a timed script for the 3-minute YouTube demo video:
  [0:00–0:10] Open app, show "OFF-GRID" status, show airplane mode ON
  [0:10–0:30] Hold RECORD, speak RED patient, show transcription
  [0:30–0:45] Progress bar, "Gemma 4 analyzing...", RED card appears
  [0:45–1:00] Phone speaks instructions aloud (TTS demo)
  [1:00–1:30] Follow-up: "no oxygen" → Gemma answers → spoken aloud
  [1:30–1:45] Say "next patient", speak GREEN patient, GREEN card
  [1:45–2:00] Show SMS payload that was dispatched
  [2:00–2:20] Python demo (terminal) as backup
  [2:20–2:40] Architecture diagram (show spec diagram)
  [2:40–3:00] GitHub repo, Kaggle page, Operation Zero-Signal title card
  Commit: "docs: add 3-minute video script for YouTube submission"

TASK E — Final checks
  Verify: ./gradlew :app:testDebugUnitTest  (all pass)
  Verify: AndroidManifest.xml has NO android.permission.INTERNET
  Verify: COORDINATOR_NUMBER in QueueManager.kt is updated from placeholder
  Verify: README.md links are correct (GitHub repo public)
  Verify: Kaggle writeup is ≤1500 words
  Verify: All docs/features/*.md exist (one per phase)
  Invoke: superpowers:requesting-code-review skill on the full submission

SUBMISSION CHECKLIST (from spec):
  - [ ] Kaggle writeup submitted (≤1500 words)
  - [ ] YouTube video uploaded (≤3 minutes, public)
  - [ ] GitHub repo public with complete README
  - [ ] APK release build available
  - [ ] Python demo runs from cold start
  - [ ] Evaluation accuracy ≥85% documented
```

---

## Emergency Recovery Prompt
**Use this if a session goes wrong and you need to understand current state.**

```
You are recovering context on the Gemma Triage Android hackathon project
(deadline May 18 2026). Something went wrong in a previous session and you
need to understand the current state before continuing.

Read these files in order:
1. CLAUDE.md                                                    (project rules + structure)
2. docs/superpowers/specs/2026-05-04-gemma-triage-design.md     (full spec)
3. docs/superpowers/plans/2026-05-04-gemma-triage-plan.md       (full plan)
4. docs/features/                                                (what's already done)

Then run:
  git log --oneline -20                                          (recent commits)
  ./gradlew :app:testDebugUnitTest 2>&1 | tail -20              (test status)
  ./gradlew :app:compileDebugKotlin 2>&1 | tail -20             (build status)

Report:
  1. What phases are complete (based on feature docs + git log)
  2. What phase is in-progress or broken
  3. What tests are failing (if any)
  4. Recommended next step

Then ask the user which phase to continue from.
```

---

## Parallel Tasks Prompt
**Use when multiple independent tasks can run concurrently (e.g. docs + tests).**

```
You are coordinating parallel work on the Gemma Triage Android app.
The following tasks are INDEPENDENT and can run in parallel:

AGENT 1 — Write evaluation test cases
  Read: android/app/src/main/assets/prompts/few_shot_examples.json
  Task: Add 20 test cases to model/evaluation/test_cases.json
        (5 per category: RED, YELLOW, GREEN, BLACK — no duplicates from few_shot)
  Output: updated test_cases.json committed

AGENT 2 — Write Kaggle writeup
  Read: docs/superpowers/specs/2026-05-04-gemma-triage-design.md
        docs/riya-pipeline-walkthrough.md
  Task: Write docs/kaggle_writeup.md (≤1500 words, all sections filled)
  Output: kaggle_writeup.md committed

AGENT 3 — Update README
  Read: docs/superpowers/specs/2026-05-04-gemma-triage-design.md  (for architecture)
        CLAUDE.md  (for tech stack)
  Task: Write Gemma-traige/gemma-triage/README.md (full submission README)
  Output: README.md committed

Dispatch all three agents simultaneously. Each is independent — no shared files.
Review each result when done. Then run: git log --oneline -5 to verify all 3 committed.
```
