# Feature: Phase 3 — Android UI

**Phase:** 3 | **Status:** complete

## What It Does

Full dark-mode UI wired to all 10 `TriageUiState` states. Shows triage code in large text coloured by severity, confidence %, reasoning, and immediate steps. A scrollable conversation panel shows the follow-up Q&A history. A "Next Patient" button resets the pipeline.

## Key Files

- `res/layout/activity_main.xml` — single-activity layout: status bar, result card, conversation scroll, speaking indicator, patient counter, Start/Next buttons
- `res/values/colors.xml` — triage palette (`triage_red`, `triage_yellow`, `triage_green`, `triage_black`) + dark-mode chrome
- `res/values/strings.xml` — all user-visible strings
- `MainActivity.kt` — observes `TriageViewModel`; handles runtime mic permission via `ActivityResultContracts`; renders each of the 10 UI states; colours triage code text per severity

## How to Test

```bash
./gradlew.bat ":app:assembleDebug"
# Install on device: ./gradlew.bat ":app:installDebug"
```

UI states to verify:
- Idle → tap Start Triage → request mic permission
- Listening → Transcribing → Analyzing → ResultReady (coloured code shown)
- Speaking → FollowUpListening → FollowUpSpeaking (conversation panel fills)
- Error state shown as status text

## Known Limitations

- No launcher icon (`mipmap/ic_launcher` removed from manifest for hackathon build)
- Conversation panel is read-only; no text input field (voice-only by design)
- Dark theme only; system theme not respected
