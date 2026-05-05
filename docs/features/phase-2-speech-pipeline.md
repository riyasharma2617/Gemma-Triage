# Feature: Phase 2 — Speech Pipeline

**Phase:** 2 | **Status:** complete

## What It Does

Implements the full offline voice I/O pipeline: Android `SpeechRecognizer` (offline STT) captures the paramedic's voice, `TextToSpeechManager` reads the triage result aloud in priority order (code → summary → steps), and `ConversationManager` maintains per-patient Q&A history for the follow-up loop.

## Key Files

- `audio/SpeechToTextManager.kt` — offline STT using `SpeechRecognizer` with `EXTRA_PREFER_OFFLINE=true`; emits `STTState` flow
- `audio/TextToSpeechManager.kt` — offline TTS at 0.85× rate; speaks code → spokenSummary → immediateSteps in sequence; emits `TTSState.Done` after last utterance
- `inference/ConversationManager.kt` — tracks per-patient initial result + Q&A history; builds thinking-mode follow-up prompt; detects "next patient" keyword
- `viewmodel/TriageUiState.kt` — 10-state sealed class covering all pipeline transitions
- `viewmodel/TriageViewModel.kt` — MVVM orchestration; observes STT→inference→TTS→STT loop; fires SMS once at initial classification

## How to Test

```bash
./gradlew.bat ":app:testDebugUnitTest"
# 9/9 tests pass
```

Manual: tap Start Triage, speak patient description, hear triage code spoken back, ask follow-up questions.

## Known Limitations

- STT relies on Android's built-in offline model; quality varies by device and language pack
- Follow-up inference uses `temp=0.3f` with max 768 tokens — on Gemma E2B this takes 3–8 s per response
- "Next patient" detection is keyword-match only (no NLU)
