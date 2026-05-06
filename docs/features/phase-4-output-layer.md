# Feature: Phase 4 — Output Layer
**Phase:** 4 | **Status:** complete

## What It Does
Persists each triage result to a local Room database and fires a single compressed SMS to the coordinator via QueueManager. SMS fires exactly once at initial triage classification — never inside the conversation follow-up loop.

## Key Files
- `android/app/src/main/java/com/gemma/triage/output/QueueManager.kt` — in-memory queue (thread-safe) with enqueue/processQueue/retryFailed; production path uses SmsManager.sendTextMessage
- `android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt` — process(result, transcription): saves TriageRecord to Room DB then enqueues+fires SMS via QueueManager
- `android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt` — Room entity: id, timestamp, triageCode, confidence, transcription, smsPayload, isTransmitted
- `android/app/src/main/java/com/gemma/triage/storage/DatabaseHelper.kt` — Room AppDatabase singleton + TriageDao
- `android/app/src/test/java/com/gemma/triage/OutputLayerTest.kt` — 11 unit tests for QueueManager and TriageOutputManager

## How to Test
```bash
./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.OutputLayerTest"
```

## Known Limitations
- `isTransmitted` field in TriageRecord is always stored as `false` — updating it to `true` after confirmed SMS delivery requires a DB update callback not implemented for the hackathon
- `SmsManager.getDefault()` is deprecated on API 31+; production should use `context.getSystemService(SmsManager::class.java)` — deferred post-hackathon
- Room database uses version 1 with no migration strategy; clearing app data resets all records
