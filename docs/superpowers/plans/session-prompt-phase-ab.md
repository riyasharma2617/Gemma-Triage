# Session Prompt — Phase A + B: Navigation Refactor + Material 3 Triage UI

> Paste this entire document as your first message in a new Claude Code session opened in `s:/Gemma-Triage`.

---

## Your Mission

You are implementing **Phase A** (Navigation Refactor) and **Phase B** (Material 3 Triage UI + Animations) of the Gemma Triage Android app. The full implementation plan is at `docs/superpowers/plans/2026-05-07-ui-history-icon-plan.md`. Read it before starting.

**Do NOT implement Phase C or Phase D** — those run in a separate session.

---

## Project Context

**App:** Offline Android disaster triage app. Voice in → Gemma on-device AI → RED/YELLOW/GREEN/BLACK triage result + spoken instructions → follow-up voice Q&A → SMS to coordinator. Zero internet connectivity.

**Tech stack:** Kotlin, Android SDK 26+, compileSdk 35, Material 3 (`com.google.android.material:1.12.0`), Room 2.6.0, MediaPipe LiteRT, MVVM + StateFlow, Android TTS + SpeechRecognizer.

**Working directory:** `s:/Gemma-Triage`
**Build tool:** `./gradlew` from inside `android/` subdirectory
**All gradle commands must be run from:** `cd android && ./gradlew ...`

---

## Current File Structure (before your changes)

```
android/app/src/main/java/com/gemma/triage/
  MainActivity.kt                  ← single-activity, holds all triage UI logic
  inference/
    GemmaInferenceEngine.kt
    PromptBuilder.kt
    TriageSchema.kt                ← TriageResult, TriageCode, RawTriageResult
    ConversationManager.kt
  audio/
    SpeechToTextManager.kt         ← STTState flow
    TextToSpeechManager.kt         ← TTSState flow
    AudioCaptureManager.kt
    VADDetector.kt
    NoiseSuppressor.kt
  output/
    SMSFormatter.kt
    QueueManager.kt
    TriageOutputManager.kt
  storage/
    DatabaseHelper.kt              ← Room AppDatabase + TriageDao
    models/TriageRecord.kt
    AudioEncryption.kt
  viewmodel/
    TriageViewModel.kt
    TriageUiState.kt               ← sealed class with Idle/Listening/Transcribing/Analyzing/ResultReady/Speaking/FollowUpListening/FollowUpAnalyzing/FollowUpSpeaking/Error
  utils/
    BatteryOptimizer.kt
    PermissionsHelper.kt
android/app/src/main/res/
  layout/activity_main.xml         ← current single-screen layout (plain LinearLayout)
  values/colors.xml                ← triage_red/yellow/green/black, background_dark, surface, accent_blue
  values/strings.xml
android/app/src/main/AndroidManifest.xml
android/app/build.gradle.kts      ← Material 1.12.0 already present, needs viewpager2 + fragment-ktx
```

---

## What Phase A Builds

Refactors `MainActivity` from a monolithic single-screen activity into a **ViewPager2 shell** hosting two Fragments:
- **Page 0 — `TriageFragment`**: all current triage workflow logic (moved from MainActivity)
- **Page 1 — `HistoryFragment`**: stub only (Phase C will implement it fully)

A 2-tab `TabLayout` at the bottom shows "Triage" / "History" labels.

**New files:** `TriagePagerAdapter.kt`, `TriageFragment.kt`, `HistoryFragment.kt` (stub), `fragment_triage.xml` (copy of current layout), `fragment_history.xml` (stub)

**Modified files:** `MainActivity.kt` (thin shell), `activity_main.xml` (ViewPager2 + TabLayout), `build.gradle.kts` (add 3 deps)

## What Phase B Builds

Upgrades `fragment_triage.xml` and `TriageFragment.kt` to full **Material 3** with animations:
- `ExtendedFloatingActionButton` (full-width mic button, label changes per state)
- `MaterialCardView` with stroke color matching triage code
- `LinearProgressIndicator` (indeterminate, shows during Listening/Analyzing)
- ObjectAnimator **pulse ring** around FAB while listening
- `ValueAnimator.ofArgb` **card background flash** on result
- `OvershootInterpolator` **scale-in** on triage code text
- `MaterialButton` (outlined) Next Patient button with **slide-up animation**
- `RecyclerView` + `ConversationBubbleAdapter` for follow-up Q&A chat bubbles

**New files:** `ConversationBubbleAdapter.kt`, `item_conversation_bubble.xml`, `shape_pulse_circle.xml`

**Modified files:** `fragment_triage.xml` (full Material 3 overhaul), `TriageFragment.kt` (all animations), `strings.xml` (new strings), `colors.xml` (add `bubble_answer`)

---

## Mandatory Rules (from CLAUDE.md)

1. **Commit after every task.** Format: `feat:`, `fix:`, `chore:`, `docs:`, `test:`
2. **Never add `android.permission.INTERNET`** to AndroidManifest.xml. Verify before each commit.
3. **Feature doc** required after each phase: `docs/features/<name>.md`
4. **TDD:** Write failing test first, then implement, then confirm pass. (Phase A/B UI code is hard to unit-test — write compile checks instead.)
5. **Phase gate:** After both A and B complete, run `./gradlew :app:testDebugUnitTest` + `./gradlew :app:assembleDebug`.

---

## How to Start

**Step 1:** Use the `superpowers:subagent-driven-development` skill — invoke it via the `Skill` tool before doing anything else.

**Step 2:** Read the full plan:
```
docs/superpowers/plans/2026-05-07-ui-history-icon-plan.md
```
Execute **Phase A tasks (A1–A8)** then **Phase B tasks (B1–B6)** in order.

**Step 3:** After Phase A compiles, run:
```bash
cd android && ./gradlew :app:compileDebugKotlin
```

**Step 4:** After Phase B compiles, run:
```bash
cd android && ./gradlew :app:assembleDebug
```

---

## Key Code References (so you don't need to read every file)

### TriageUiState (all states you must handle in TriageFragment)
```kotlin
sealed class TriageUiState {
    object Idle : TriageUiState()
    object Listening : TriageUiState()
    data class Transcribing(val text: String) : TriageUiState()
    object Analyzing : TriageUiState()
    data class ResultReady(val result: TriageResult, val transcription: String) : TriageUiState()
    data class Speaking(val stage: String) : TriageUiState()
    object FollowUpListening : TriageUiState()
    object FollowUpAnalyzing : TriageUiState()
    data class FollowUpSpeaking(val question: String, val answer: String) : TriageUiState()
    data class Error(val message: String) : TriageUiState()
}
```

### TriageResult fields you display
```kotlin
data class TriageResult(
    val triageCode: TriageCode,   // RED/YELLOW/GREEN/BLACK/UNKNOWN
    val confidence: Double,
    val reasoning: String,
    val immediateSteps: List<String>,
    val smsPayload: String,
    // ... other fields not used in UI
)
enum class TriageCode { RED, YELLOW, GREEN, BLACK, UNKNOWN }
```

### TriageViewModel public API (use activityViewModels() in fragments)
```kotlin
val uiState: StateFlow<TriageUiState>
val patientCount: StateFlow<Int>
val modelReady: StateFlow<Boolean>
fun startListening()
fun stopListening()
fun resetToNextPatient()
```

### Existing colors (reference in layouts)
```
@color/background_dark  #121212
@color/surface          #1E1E1E
@color/on_surface       #FFFFFF
@color/on_surface_secondary #B0B0B0
@color/accent_blue      #1565C0
@color/triage_red       #D32F2F
@color/triage_yellow    #F9A825
@color/triage_green     #388E3C
@color/triage_black     #212121
@color/triage_unknown   #757575
```

### Build commands
```bash
# All from android/ subdirectory
cd android && ./gradlew :app:compileDebugKotlin    # fast compile check
cd android && ./gradlew :app:testDebugUnitTest      # unit tests
cd android && ./gradlew :app:assembleDebug          # full build
```

---

## Completion Criteria

Phase A complete when:
- [ ] `./gradlew :app:compileDebugKotlin` passes
- [ ] App shows two swipeable pages (Triage + History stub)
- [ ] All triage workflow still works from TriageFragment
- [ ] Committed

Phase B complete when:
- [ ] `./gradlew :app:assembleDebug` passes
- [ ] Mic FAB pulses during listening
- [ ] Card flashes triage color on result
- [ ] Triage code scales in with overshoot
- [ ] Next patient button slides up
- [ ] Committed
- [ ] Feature doc at `docs/features/ui-material3-overhaul.md` created
