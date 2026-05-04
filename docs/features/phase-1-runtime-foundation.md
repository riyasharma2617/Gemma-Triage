# Feature: Runtime Foundation
**Phase:** 1 | **Status:** complete

## What It Does
MediaPipe LlmInference wired for Gemma 4 E2B INT4 on-device inference. Expanded TriageResult schema with spokenSummary, immediateSteps, monitoringChecklist, warningSigns, smsPayload. PromptBuilder loads real assets at runtime and injects 2 random few-shot examples per call.

## Key Files
- `android/app/src/main/java/com/gemma/triage/inference/GemmaInferenceEngine.kt` — MediaPipe LlmInference + JSON parser companion object + runFollowUpInference
- `android/app/src/main/java/com/gemma/triage/inference/TriageSchema.kt` — expanded TriageResult + RawTriageResult for Gson deserialization
- `android/app/src/main/java/com/gemma/triage/inference/PromptBuilder.kt` — loads system_prompt.txt + few-shot examples from assets; no-context overload for tests
- `android/app/src/main/assets/prompts/system_prompt.txt` — START protocol + expanded JSON schema instruction
- `android/app/src/main/assets/prompts/few_shot_examples.json` — 13 real triage cases
- `android/app/build.gradle` — MediaPipe tasks-genai:0.10.14, Gson 2.10.1, ViewModel, Room

## How to Test
```bash
cd android
./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.InferenceTest"
```
All 5 tests should pass. Tests exercise: clean JSON parse, preamble stripping, malformed output, BLACK code, expanded schema fields.

## Known Limitations
- LlmInference API requires Android device/emulator — unit tests test JSON parsing only, not real on-device inference
- Model file (gemma4e2b_int4.bin, ~1.3GB) must be placed in app's filesDir via `scripts/setup_model.py` before inference works
- few_shot_examples.json uses `recommendedActions` (legacy field); system_prompt.txt instructs Gemma to emit the expanded schema with `immediateSteps`, `spokenSummary`, etc.
