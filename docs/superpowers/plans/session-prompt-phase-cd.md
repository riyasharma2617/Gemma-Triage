# Session Prompt — Phase C + D: Patient History Screen + App Icon

> Paste this entire document as your first message in a new Claude Code session opened in `s:/Gemma-Triage`.
> **Prerequisite:** Phase A (Navigation Refactor) must be complete before starting Phase C. Phase D is fully independent and can start immediately.

---

## Your Mission

You are implementing **Phase C** (Patient History Screen) and **Phase D** (App Icon) of the Gemma Triage Android app. The full implementation plan is at `docs/superpowers/plans/2026-05-07-ui-history-icon-plan.md`. Read it before starting.

**Do NOT implement Phase A or Phase B** — those run in a separate session.

**Phase D is independent** — start it immediately while waiting for Phase A to complete if needed.
**Phase C requires Phase A to be complete** — `TriageFragment`, `HistoryFragment` (stub), and `TriagePagerAdapter` must already exist.

---

## Project Context

**App:** Offline Android disaster triage app. Voice in → Gemma on-device AI → RED/YELLOW/GREEN/BLACK triage result + spoken instructions → follow-up voice Q&A → SMS to coordinator. Zero internet connectivity.

**Tech stack:** Kotlin, Android SDK 26+, compileSdk 35, Material 3 (`com.google.android.material:1.12.0`), Room 2.6.0, MediaPipe LiteRT, MVVM + StateFlow, Android TTS + SpeechRecognizer.

**Working directory:** `s:/Gemma-Triage`
**Build tool:** `./gradlew` from inside `android/` subdirectory
**All gradle commands must be run from:** `cd android && ./gradlew ...`

---

## Current File Structure (after Phase A/B complete)

```
android/app/src/main/java/com/gemma/triage/
  MainActivity.kt                  ← thin ViewPager2 shell (Phase A done)
  TriagePagerAdapter.kt            ← Phase A done
  TriageFragment.kt                ← Phase B done (Material 3 + animations)
  HistoryFragment.kt               ← STUB only — you will implement this
  ConversationBubbleAdapter.kt     ← Phase B done
  HistoryExpandState.kt            ← YOU CREATE THIS (Phase C)
  HistoryAdapter.kt                ← YOU CREATE THIS (Phase C)
  inference/
    GemmaInferenceEngine.kt
    PromptBuilder.kt
    TriageSchema.kt                ← TriageResult, TriageCode
    ConversationManager.kt
  audio/
    SpeechToTextManager.kt
    TextToSpeechManager.kt
  output/
    SMSFormatter.kt
    QueueManager.kt
    TriageOutputManager.kt         ← YOU MODIFY: add immediateSteps field
  storage/
    DatabaseHelper.kt              ← YOU MODIFY: version 1→2 + fallbackToDestructiveMigration
    models/TriageRecord.kt         ← YOU MODIFY: add immediateSteps: String field
  viewmodel/
    TriageViewModel.kt             ← YOU MODIFY: add history: StateFlow<List<TriageRecord>>
    TriageUiState.kt
android/app/src/main/res/
  layout/
    activity_main.xml              ← ViewPager2 + TabLayout (Phase A done)
    fragment_triage.xml            ← Material 3 layout (Phase B done)
    fragment_history.xml           ← STUB — you will replace this
    item_history_record.xml        ← YOU CREATE THIS
    item_conversation_bubble.xml   ← Phase B done
  drawable/
    shape_pulse_circle.xml         ← Phase B done
    ic_launcher_foreground.xml     ← YOU CREATE THIS (Phase D)
    ic_launcher_background.xml     ← YOU CREATE THIS (Phase D)
    ic_launcher_monochrome.xml     ← YOU CREATE THIS (Phase D)
  mipmap-anydpi-v26/
    ic_launcher.xml                ← YOU CREATE THIS (Phase D)
    ic_launcher_round.xml          ← YOU CREATE THIS (Phase D)
  values/
    colors.xml                     ← bubble_answer color already added (Phase B)
    strings.xml                    ← new strings already added (Phase B)
android/app/src/main/AndroidManifest.xml ← YOU ADD icon refs (Phase D)
android/app/src/test/java/com/gemma/triage/
  HistoryExpandStateTest.kt        ← YOU CREATE THIS (Phase C, TDD)
```

---

## What Phase C Builds

Full **patient history screen** replacing the `HistoryFragment` stub:

1. **`TriageRecord` schema update** — add `immediateSteps: String` field, bump Room DB to version 2 with `fallbackToDestructiveMigration()`
2. **`TriageOutputManager`** — pass `result.immediateSteps.joinToString("\n")` to the new field
3. **`TriageViewModel`** — add `val history: StateFlow<List<TriageRecord>>`, load from Room on init and after each patient processed
4. **`HistoryExpandState`** — pure Kotlin class tracking which card is expanded (TDD: write test first)
5. **`HistoryAdapter`** — `RecyclerView.Adapter` with expandable `MaterialCardView` cards
6. **`HistoryFragment`** — observes `viewModel.history`, drives RecyclerView, shows today's count header + empty state
7. **Layouts** — `fragment_history.xml` (full), `item_history_record.xml` (expandable card)

## What Phase D Builds

Custom **adaptive launcher icon**:
- `ic_launcher_foreground.xml` — white medical cross + RED→YELLOW→GREEN arc
- `ic_launcher_background.xml` — deep navy `#0A1628` fill
- `ic_launcher_monochrome.xml` — cross silhouette only (Android 13+ themed icons)
- `mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml` — adaptive icon manifests
- `AndroidManifest.xml` — add `android:icon` + `android:roundIcon` to `<application>`

---

## Mandatory Rules (from CLAUDE.md)

1. **TDD for Phase C:** Write `HistoryExpandStateTest.kt` with failing tests FIRST, implement `HistoryExpandState.kt`, confirm tests pass.
2. **Commit after every task.** Format: `feat:`, `fix:`, `chore:`, `docs:`, `test:`
3. **Never add `android.permission.INTERNET`** to AndroidManifest.xml. Verify: `grep -n "INTERNET" android/app/src/main/AndroidManifest.xml` — must return nothing.
4. **Feature docs** required: `docs/features/patient-history-screen.md` + `docs/features/app-icon.md`
5. **Phase gate:** After both C and D complete, run `./gradlew :app:testDebugUnitTest` + `./gradlew :app:assembleDebug` — both must pass.

---

## How to Start

**Step 1:** Use the `superpowers:subagent-driven-development` skill — invoke it via the `Skill` tool before doing anything else.

**Step 2:** Read the full plan:
```
docs/superpowers/plans/2026-05-07-ui-history-icon-plan.md
```
Execute **Phase D tasks (D1–D5) first** (independent, fast), then **Phase C tasks (C1–C9)**.

---

## Key Code References

### Current TriageRecord (BEFORE your changes — you add immediateSteps)
```kotlin
@Entity(tableName = "triage_records")
data class TriageRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val timestamp: Long,
    val triageCode: String,
    val confidence: Double,
    val transcription: String,
    val smsPayload: String,
    val isTransmitted: Boolean = false
)
```

### After your change (add immediateSteps between transcription and smsPayload)
```kotlin
@Entity(tableName = "triage_records")
data class TriageRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val timestamp: Long,
    val triageCode: String,
    val confidence: Double,
    val transcription: String,
    val immediateSteps: String,      // NEW — newline-joined from TriageResult.immediateSteps
    val smsPayload: String,
    val isTransmitted: Boolean = false
)
```

### TriageOutputManager.process() — what you modify
```kotlin
// CURRENT:
val record = TriageRecord(
    timestamp = System.currentTimeMillis(),
    triageCode = result.triageCode.name,
    confidence = result.confidence,
    transcription = transcription,
    smsPayload = SMSFormatter.formatForSMS(result),
    isTransmitted = false
)

// AFTER YOUR CHANGE (add immediateSteps):
val record = TriageRecord(
    timestamp = System.currentTimeMillis(),
    triageCode = result.triageCode.name,
    confidence = result.confidence,
    transcription = transcription,
    immediateSteps = result.immediateSteps.joinToString("\n"),
    smsPayload = SMSFormatter.formatForSMS(result),
    isTransmitted = false
)
```

### TriageViewModel — what you add
```kotlin
// Add these to TriageViewModel:
private val db = AppDatabase.getDatabase(context)
private val _history = MutableStateFlow<List<TriageRecord>>(emptyList())
val history: StateFlow<List<TriageRecord>> = _history

private fun loadHistory() {
    viewModelScope.launch(Dispatchers.IO) {
        _history.value = db.triageDao().getAllRecords()
    }
}
// Call loadHistory() in init{} and at end of runInitialInference() after outputManager.process()
```

### HistoryExpandState — TDD target
```kotlin
// Test these behaviors:
// 1. Initial expandedPosition is -1
// 2. toggle(2) → expandedPosition = 2, returns -1
// 3. toggle(2) again → expandedPosition = -1, returns 2
// 4. toggle(2) then toggle(5) → expandedPosition = 5, returns 2 (old)
// 5. toggle when nothing expanded returns -1

class HistoryExpandState {
    var expandedPosition: Int = -1
    fun toggle(position: Int): Int {
        val old = expandedPosition
        expandedPosition = if (old == position) -1 else position
        return old
    }
}
```

### HistoryFragment key logic
```kotlin
class HistoryFragment : Fragment() {
    private val viewModel: TriageViewModel by activityViewModels()
    private val adapter = HistoryAdapter()

    // Observe viewModel.history, submitList to adapter
    // Count records with today's date for header
    // Show/hide empty state TextView
}
```

### HistoryAdapter expand behavior
```kotlin
// One card expanded at a time
// click → TransitionManager.beginDelayedTransition on rvParent, toggle visibility
// notifyItemChanged on old expanded position to collapse it
```

### Existing colors (for history card styling)
```
@color/background_dark  #121212
@color/surface          #1E1E1E
@color/on_surface       #FFFFFF
@color/on_surface_secondary #B0B0B0
@color/accent_blue      #1565C0
@color/triage_red       #D32F2F   (use for RED chip background)
@color/triage_yellow    #F9A825   (use for YELLOW chip background)
@color/triage_green     #388E3C   (use for GREEN chip background)
@color/triage_black     #212121   (use for BLACK chip background)
```

### Strings already added to strings.xml (by Phase B session)
```xml
<string name="label_patients_triaged">Patients triaged: %d</string>
<string name="label_no_history">No patients triaged yet.</string>
<string name="label_patients_today">%d patient(s) today</string>
<string name="label_transcription">Transcription</string>
<string name="label_steps">Immediate Steps</string>
<string name="label_sms">SMS Payload</string>
<string name="label_sms_sent">SMS sent</string>
<string name="label_sms_pending">Pending</string>
```

### DatabaseHelper — version bump you make
```kotlin
// Change version = 1 to version = 2
@Database(entities = [TriageRecord::class], version = 2)
abstract class AppDatabase : RoomDatabase() { ... }

// Add .fallbackToDestructiveMigration() in databaseBuilder chain:
Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, "triage_database")
    .fallbackToDestructiveMigration()
    .build()
```

### App icon design (Phase D)
- **Foreground:** White medical cross (10×40dp vertical, 40×10dp horizontal bars, centered in 108×108 viewport) + triage arc (3 path segments: RED bottom-left, YELLOW bottom, GREEN bottom-right)
- **Background:** Solid navy fill `#0A1628`
- **Monochrome:** Cross only (no arc), white, for Android 13+ themed icons
- All files go in `res/drawable/`, adaptive icon manifests in `res/mipmap-anydpi-v26/`

### Build commands
```bash
# All from android/ subdirectory
cd android && ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.HistoryExpandStateTest"
cd android && ./gradlew :app:compileDebugKotlin
cd android && ./gradlew :app:testDebugUnitTest
cd android && ./gradlew :app:assembleDebug
```

---

## Completion Criteria

Phase D complete when:
- [ ] `ic_launcher_foreground.xml`, `ic_launcher_background.xml`, `ic_launcher_monochrome.xml` created
- [ ] `mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml` created
- [ ] `AndroidManifest.xml` has `android:icon="@mipmap/ic_launcher"` and `android:roundIcon="@mipmap/ic_launcher_round"`
- [ ] `./gradlew :app:compileDebugKotlin` passes
- [ ] Feature doc at `docs/features/app-icon.md` committed

Phase C complete when:
- [ ] `HistoryExpandStateTest` — all 5 tests pass
- [ ] `TriageRecord` has `immediateSteps: String` field
- [ ] Room DB at version 2 with `fallbackToDestructiveMigration()`
- [ ] `TriageViewModel.history` StateFlow populated from DB
- [ ] History page shows expandable cards with full detail on tap
- [ ] Today's patient count shown in header
- [ ] Empty state shown when no records
- [ ] `./gradlew :app:assembleDebug` passes
- [ ] Feature doc at `docs/features/patient-history-screen.md` committed
- [ ] No `android.permission.INTERNET` in manifest
