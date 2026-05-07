# Feature: Material 3 UI Overhaul
**Phase:** UI Overhaul | **Status:** complete

## What It Does
Upgrades the triage screen from a plain LinearLayout to Material 3 components with animations: mic pulse (ObjectAnimator), triage code scale-in (OvershootInterpolator), card color flash (ValueAnimator), progress indicator, conversation bubbles (RecyclerView), and Next Patient slide-up.

## Key Files
- `android/app/src/main/java/com/gemma/triage/TriageFragment.kt` — all triage UI + animation logic
- `android/app/src/main/java/com/gemma/triage/ConversationBubbleAdapter.kt` — chat bubble RecyclerView
- `android/app/src/main/res/layout/fragment_triage.xml` — Material 3 layout

## How to Test
Run app on device/emulator, tap "Start Triage", observe pulse animation. Say symptoms, observe card flash + code scale-in.

## Known Limitations
Single pulse ring (not 3 rings). PNG mipmap fallbacks not generated (not needed, minSdk=26).
