# Feature: Output Layer (Phase 4)
**Phase:** 4 | **Status:** complete

## What It Does
Implements the complete output pipeline: QueueManager buffers TriageResult items and fires SMS via a pluggable sender, TriageOutputManager orchestrates one-shot SMS dispatch plus Room DB persistence per patient — exactly once at initial classification, never during follow-up conversation.

## Key Files
- `android/app/src/main/java/com/gemma/triage/output/QueueManager.kt` — pending/failed queues, processQueue, retryFailed, updateSmsSender
- `android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt` — primary constructor (Context, production SMS + Room), secondary constructor (coordinatorPhone, smsSender lambda, dbWriter lambda) for testability
- `android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt` — updated entity: `transcription` (renamed from patientDescription), `smsPayload` (new field)
- `android/app/src/test/java/com/gemma/triage/OutputLayerTest.kt` — 11 unit tests covering enqueue, processQueue, retryFailed, TriageOutputManager.process()
- `android/app/build.gradle.kts` — migrated `annotationProcessor` → `kapt` for Room
- `android/build.gradle.kts` — added `org.jetbrains.kotlin.kapt` plugin declaration

## How to Test
```bash
./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.OutputLayerTest"
./gradlew :app:testDebugUnitTest   # all tests
./gradlew :app:assembleDebug       # full build
```

## Known Limitations
- `SmsManager.getDefault()` is deprecated on API 31+; production path should use `context.getSystemService(SmsManager::class.java)`. Suppressed for hackathon deadline — the lambda constructor path used in tests bypasses this entirely.
- kapt warns "doesn't support language version 2.0+, falling back to 1.9" — benign for Room annotation processing, no functional impact.
- Room DB version is still 1; the TriageRecord schema change (rename + new field) will require a migration or destructive rebuild on devices that already have the DB from a prior install.
