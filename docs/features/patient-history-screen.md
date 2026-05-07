# Feature: Patient History Screen
**Phase:** UI Overhaul | **Status:** complete

## What It Does
Adds a swipe-left history page (ViewPager2 page 1) showing all past triage patients as expandable MaterialCardView entries. Tap to reveal full transcription, immediate steps, SMS payload, and transmission status.

## Key Files
- `android/app/src/main/java/com/gemma/triage/HistoryFragment.kt` — history screen Fragment
- `android/app/src/main/java/com/gemma/triage/HistoryAdapter.kt` — expandable RecyclerView adapter
- `android/app/src/main/java/com/gemma/triage/HistoryExpandState.kt` — pure Kotlin expand/collapse tracker
- `android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt` — added immediateSteps field
- `android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt` — added history StateFlow

## How to Test
Run app, triage a patient. Swipe left to History page. Card shows code badge + timestamp. Tap card to expand full detail.

## Known Limitations
isTransmitted flag stays false (SMS delivery callback not wired to DB update — known prior limitation). History sorted newest-first from DB.
