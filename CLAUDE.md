# Gemma Triage — CLAUDE.md

## Project in One Sentence
Offline Android disaster triage app: voice in → Gemma 4 on-device (MediaPipe LiteRT) → RED/YELLOW/GREEN/BLACK + spoken instructions → follow-up voice conversation → SMS to coordinator. **Hackathon deadline: May 18 2026.**

## Tech Stack
- Kotlin, Android SDK 26+, `compileSdk 34`
- MediaPipe `tasks-genai:0.10.14` — Gemma 4 E2B INT4 on-device
- AndroidX ViewModel + StateFlow (MVVM), `activity-ktx:1.8.2`
- Android `TextToSpeech` + `SpeechRecognizer` (both offline, no internet)
- Room `2.6.0`, Android `SmsManager`, Gson `2.10.1`
- Coroutines `1.7.3`

## File Structure
```
android/app/src/main/java/com/gemma/triage/
  audio/           AudioCaptureManager, VADDetector, SpeechToTextManager, TextToSpeechManager
  inference/       GemmaInferenceEngine, PromptBuilder, TriageSchema, ConversationManager
  output/          SMSFormatter, QueueManager, TriageOutputManager
  storage/         DatabaseHelper, models/TriageRecord
  utils/           BatteryOptimizer, PermissionsHelper
  viewmodel/       TriageViewModel, TriageUiState
  MainActivity.kt
android/app/src/main/assets/prompts/
  system_prompt.txt
  few_shot_examples.json
android/app/src/test/java/com/gemma/triage/
  InferenceTest.kt
docs/
  features/        <-- one .md per implemented feature
  riya-pipeline-walkthrough.md
  superpowers/
    specs/         2026-05-04-gemma-triage-design.md
    plans/         2026-05-04-gemma-triage-plan.md
                   2026-05-04-subagent-execution-prompts.md
python_demo/
  triage_demo.py
  requirements.txt
scripts/
  setup_model.py
```

## Recurring Rules — Follow These Every Time

### Rule 1 — Feature Doc on Every Feature
After implementing any feature or completing any phase task, create:
```
docs/features/<kebab-case-feature-name>.md
```
Template:
```markdown
# Feature: <Name>
**Phase:** <phase number> | **Status:** complete

## What It Does
<1-2 sentences>

## Key Files
- `path/to/file.kt` — <responsibility>

## How to Test
<exact command or manual steps>

## Known Limitations
<any known gaps or shortcuts taken for hackathon deadline>
```
Commit the feature doc in the same commit as the feature code.

### Rule 2 — TDD: Test First
Write the failing unit test BEFORE writing implementation code.
Run: `./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.<TestClass>"`
Confirm it fails, then implement, then confirm it passes.

### Rule 3 — Commit After Every Task
One commit per task. Format:
```
feat: <what was added>       # new functionality
fix: <what was fixed>        # bug fix
docs: <doc changes only>     # documentation
chore: <build/config>        # gradle, manifests, config
test: <test changes only>    # tests without prod code change
```

### Rule 4 — Phase Completion Gate
After every phase:
1. Run: `./gradlew :app:testDebugUnitTest` — all must pass
2. Run: `./gradlew :app:assembleDebug` — must BUILD SUCCESSFUL
3. Invoke the `superpowers:requesting-code-review` skill
4. Update the relevant feature docs if anything changed

### Rule 5 — Never Add INTERNET Permission
`AndroidManifest.xml` must NEVER have `android.permission.INTERNET`. The whole point is zero-connectivity. Verify this before every phase completion.

### Rule 6 — SMS Fires Once Per Patient
`TriageOutputManager.process()` fires SMS exactly once at initial classification. The conversation follow-up loop is local only. Never add SMS sends inside `ConversationManager` or `runFollowUpInference`.

## Architecture at a Glance
```
SpeechToTextManager (offline STT)
  → PromptBuilder (Gemma chat template + system_prompt + few-shot)
  → GemmaInferenceEngine.runTriageInference() [temp=0.1, 512 tokens]
  → TriageResult (triageCode, spokenSummary, immediateSteps,
                  monitoringChecklist, warningSigns, smsPayload)
  → TriageOutputManager → Room DB + SMS (ONCE)
  → TextToSpeechManager.speakTriageResult() [rate=0.85]
  → TTSState.Done → ConversationManager follow-up loop
      → GemmaInferenceEngine.runFollowUpInference() [temp=0.3, 768 tokens]
      → TextToSpeechManager.speakFollowUpAnswer()
      → loop until "next patient" keyword
```

## Critical Design Decisions (Do Not Change Without Reading Spec)
| Decision | Value | Reason |
|---|---|---|
| Initial triage temperature | 0.1f | Near-deterministic — consistency matters in triage |
| Follow-up temperature | 0.3f | Needs adaptive reasoning across constraints |
| TTS speech rate | 0.85f | Slower for field noise conditions |
| SMS trigger | Once, at initial classification | Follow-up is local only |
| Model file location | `context.filesDir/gemma4e2b_int4.bin` | Assets can't hold 1.3GB |
| Max initial tokens | 512 | JSON output <200 tokens, headroom for reasoning |
| Max follow-up tokens | 768 | Thinking-mode needs more space |
| TTS order | Code → spokenSummary → immediateSteps | Code first — most time-critical |

## Key Reference Docs
- Full spec: `docs/superpowers/specs/2026-05-04-gemma-triage-design.md`
- Full plan: `docs/superpowers/plans/2026-05-04-gemma-triage-plan.md`
- Pipeline walkthrough: `docs/riya-pipeline-walkthrough.md`
- Phased execution prompts: `docs/superpowers/plans/2026-05-04-subagent-execution-prompts.md`

## Skills to Use
| Situation | Skill |
|---|---|
| Starting a new conversation on this project | `superpowers:using-superpowers` |
| About to build a new feature | `superpowers:brainstorming` |
| Writing an implementation plan | `superpowers:writing-plans` |
| Executing a plan task-by-task | `superpowers:executing-plans` |
| Multiple independent tasks | `superpowers:dispatching-parallel-agents` |
| Hit a bug or unexpected behavior | `superpowers:systematic-debugging` |
| About to claim work is complete | `superpowers:verification-before-completion` |
| Finished a phase | `superpowers:requesting-code-review` |
| Receiving review feedback | `superpowers:receiving-code-review` |
| Updating CLAUDE.md | `claude-md-management:revise-claude-md` |

## Gemma Chat Template (Always Use This)
```
<start_of_turn>system
[system prompt]
<end_of_turn>
<start_of_turn>user
[user message]
<end_of_turn>
<start_of_turn>model
```

## Build Commands
```bash
# Run unit tests
./gradlew :app:testDebugUnitTest

# Run specific test class
./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.InferenceTest"

# Build debug APK
./gradlew :app:assembleDebug

# Install on connected device
./gradlew :app:installDebug

# Check for compilation errors only (faster)
./gradlew :app:compileDebugKotlin
```
