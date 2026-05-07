# UI Overhaul, Patient History, and App Icon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Gemma Triage to a two-page Material 3 app (swipe-left = history), with animated triage interactions and a custom launcher icon.

**Architecture:** `ViewPager2` in `MainActivity` hosts `TriageFragment` (all existing triage logic) and `HistoryFragment` (RecyclerView of past patients). Both fragments share `TriageViewModel` via `activityViewModels()`. `TriageRecord` gains an `immediateSteps` field (Room DB v2, `fallbackToDestructiveMigration`).

**Tech Stack:** Material 3 `1.12.0` (already in project), `ViewPager2 1.0.0` (new dep), `fragment-ktx 1.6.2` (new dep), Room `2.6.0` (existing), `ObjectAnimator`/`ValueAnimator` (built-in).

---

## Parallel Execution Note

- **Phase D** is fully independent — run immediately in parallel with Phase A.
- **Phase A** must complete before B and C start.
- **Phases B and C** can run in parallel after A completes.

**Recommended order:**
1. Start Phase A + Phase D simultaneously
2. After A: start Phase B + Phase C simultaneously

---

## File Map

### New Files
| Path | Purpose |
|------|---------|
| `android/app/src/main/java/com/gemma/triage/TriagePagerAdapter.kt` | ViewPager2 adapter |
| `android/app/src/main/java/com/gemma/triage/TriageFragment.kt` | Triage screen Fragment |
| `android/app/src/main/java/com/gemma/triage/HistoryFragment.kt` | History screen Fragment |
| `android/app/src/main/java/com/gemma/triage/HistoryAdapter.kt` | RecyclerView adapter for history |
| `android/app/src/main/java/com/gemma/triage/HistoryExpandState.kt` | Pure Kotlin expand/collapse logic |
| `android/app/src/main/java/com/gemma/triage/ConversationBubbleAdapter.kt` | Chat bubbles adapter |
| `android/app/src/main/res/layout/fragment_triage.xml` | Triage screen layout |
| `android/app/src/main/res/layout/fragment_history.xml` | History screen layout |
| `android/app/src/main/res/layout/item_history_record.xml` | History list card |
| `android/app/src/main/res/layout/item_conversation_bubble.xml` | Chat bubble card |
| `android/app/src/main/res/drawable/shape_pulse_circle.xml` | Oval drawable for mic pulse |
| `android/app/src/main/res/drawable/ic_launcher_foreground.xml` | Launcher icon foreground vector |
| `android/app/src/main/res/drawable/ic_launcher_background.xml` | Launcher icon background |
| `android/app/src/main/res/drawable/ic_launcher_monochrome.xml` | Monochrome icon (Android 13+) |
| `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml` | Adaptive icon manifest |
| `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml` | Round adaptive icon manifest |
| `android/app/src/test/java/com/gemma/triage/HistoryExpandStateTest.kt` | Unit test for expand state |
| `docs/features/ui-material3-overhaul.md` | Feature doc |
| `docs/features/patient-history-screen.md` | Feature doc |
| `docs/features/app-icon.md` | Feature doc |

### Modified Files
| Path | Change |
|------|--------|
| `android/app/build.gradle.kts` | Add ViewPager2, fragment-ktx, recyclerview |
| `android/app/src/main/java/com/gemma/triage/MainActivity.kt` | Thin shell hosting ViewPager2 |
| `android/app/src/main/res/layout/activity_main.xml` | Replace with ViewPager2 + TabLayout |
| `android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt` | Add `immediateSteps: String` |
| `android/app/src/main/java/com/gemma/triage/storage/DatabaseHelper.kt` | Version 1→2, fallbackToDestructiveMigration |
| `android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt` | Pass `immediateSteps` to record |
| `android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt` | Add `history: StateFlow<List<TriageRecord>>` |
| `android/app/src/main/res/values/strings.xml` | Add new UI strings |
| `android/app/src/main/res/values/colors.xml` | Add `bubble_answer` color |
| `android/app/src/main/AndroidManifest.xml` | Add `android:icon` + `android:roundIcon` |

---

## Phase A: Navigation Refactor

### Task A1: Add dependencies to build.gradle.kts

**Files:** Modify `android/app/build.gradle.kts`

- [ ] **Step 1: Add three new dependencies inside the `dependencies` block**

In `android/app/build.gradle.kts`, after the `activity-ktx` line, add:
```kotlin
    implementation("androidx.viewpager2:viewpager2:1.0.0")
    implementation("androidx.fragment:fragment-ktx:1.6.2")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
```

- [ ] **Step 2: Sync gradle**
```bash
cd android && ./gradlew :app:dependencies --configuration debugRuntimeClasspath | head -20
```
Expected: exits 0 (sync succeeds).

---

### Task A2: Replace activity_main.xml with ViewPager2 shell

**Files:** Modify `android/app/src/main/res/layout/activity_main.xml`

- [ ] **Step 1: Replace the entire file content**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/background_dark">

    <androidx.viewpager2.widget.ViewPager2
        android:id="@+id/viewPager"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1" />

    <com.google.android.material.tabs.TabLayout
        android:id="@+id/tabIndicator"
        android:layout_width="match_parent"
        android:layout_height="40dp"
        android:background="@color/background_dark"
        app:tabIndicatorColor="@color/accent_blue"
        app:tabBackground="@color/background_dark"
        app:tabSelectedTextColor="@color/accent_blue"
        app:tabTextColor="@color/on_surface_secondary"
        app:tabMode="fixed" />

</LinearLayout>
```

---

### Task A3: Create TriagePagerAdapter.kt

**Files:** Create `android/app/src/main/java/com/gemma/triage/TriagePagerAdapter.kt`

- [ ] **Step 1: Create the file**

```kotlin
package com.gemma.triage

import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.viewpager2.adapter.FragmentStateAdapter

class TriagePagerAdapter(activity: FragmentActivity) : FragmentStateAdapter(activity) {
    override fun getItemCount() = 2
    override fun createFragment(position: Int): Fragment = when (position) {
        0 -> TriageFragment()
        else -> HistoryFragment()
    }
}
```

---

### Task A4: Create fragment_triage.xml (exact copy of current activity_main.xml)

**Files:** Create `android/app/src/main/res/layout/fragment_triage.xml`

- [ ] **Step 1: Create the file** (this is the existing activity_main.xml content verbatim — Phase B will upgrade it)

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/background_dark"
    android:padding="16dp">

    <TextView
        android:id="@+id/tvStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="@string/status_idle"
        android:textColor="@color/on_surface_secondary"
        android:textSize="14sp"
        android:paddingBottom="8dp" />

    <LinearLayout
        android:id="@+id/cardResult"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:orientation="vertical"
        android:background="@color/surface"
        android:padding="16dp"
        android:gravity="center"
        android:visibility="invisible">

        <TextView
            android:id="@+id/tvTriageCode"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:textSize="64sp"
            android:textStyle="bold"
            android:textColor="@color/on_surface"
            tools:text="RED" />

        <TextView
            android:id="@+id/tvConfidence"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:textSize="18sp"
            android:textColor="@color/on_surface_secondary"
            android:paddingTop="4dp"
            tools:text="97% confidence" />

        <TextView
            android:id="@+id/tvReasoning"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="14sp"
            android:textColor="@color/on_surface_secondary"
            android:paddingTop="12dp"
            tools:text="Three RED criteria met" />

        <TextView
            android:id="@+id/tvSteps"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="14sp"
            android:textColor="@color/on_surface"
            android:paddingTop="12dp"
            tools:text="1. Secure airway" />
    </LinearLayout>

    <ScrollView
        android:id="@+id/scrollConversation"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:visibility="gone">

        <TextView
            android:id="@+id/tvConversation"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textSize="14sp"
            android:textColor="@color/on_surface"
            android:padding="8dp" />
    </ScrollView>

    <TextView
        android:id="@+id/tvSpeaking"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Speaking…"
        android:textColor="@color/accent_blue"
        android:textSize="14sp"
        android:paddingVertical="8dp"
        android:visibility="gone" />

    <TextView
        android:id="@+id/tvPatientCount"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textColor="@color/on_surface_secondary"
        android:textSize="12sp"
        android:paddingBottom="8dp"
        tools:text="Patients: 0" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:gravity="center">

        <Button
            android:id="@+id/btnStartTriage"
            android:layout_width="0dp"
            android:layout_height="64dp"
            android:layout_weight="1"
            android:layout_marginEnd="8dp"
            android:text="@string/btn_start_triage"
            android:textSize="16sp"
            android:backgroundTint="@color/accent_blue" />

        <Button
            android:id="@+id/btnNextPatient"
            android:layout_width="0dp"
            android:layout_height="64dp"
            android:layout_weight="1"
            android:layout_marginStart="8dp"
            android:text="@string/btn_next_patient"
            android:textSize="16sp"
            android:backgroundTint="@color/triage_green"
            android:visibility="gone" />
    </LinearLayout>

</LinearLayout>
```

---

### Task A5: Create TriageFragment.kt (all logic from MainActivity)

**Files:** Create `android/app/src/main/java/com/gemma/triage/TriageFragment.kt`

- [ ] **Step 1: Create the file**

```kotlin
package com.gemma.triage

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.viewmodel.TriageUiState
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch

class TriageFragment : Fragment() {

    private val viewModel: TriageViewModel by activityViewModels()

    private lateinit var tvStatus: TextView
    private lateinit var cardResult: LinearLayout
    private lateinit var tvTriageCode: TextView
    private lateinit var tvConfidence: TextView
    private lateinit var tvReasoning: TextView
    private lateinit var tvSteps: TextView
    private lateinit var scrollConversation: ScrollView
    private lateinit var tvConversation: TextView
    private lateinit var tvSpeaking: TextView
    private lateinit var tvPatientCount: TextView
    private lateinit var btnStartTriage: Button
    private lateinit var btnNextPatient: Button

    private val conversationLog = StringBuilder()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants[Manifest.permission.RECORD_AUDIO] == true) {
            viewModel.startListening()
        } else {
            tvStatus.text = "Microphone permission required"
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.fragment_triage, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        tvStatus = view.findViewById(R.id.tvStatus)
        cardResult = view.findViewById(R.id.cardResult)
        tvTriageCode = view.findViewById(R.id.tvTriageCode)
        tvConfidence = view.findViewById(R.id.tvConfidence)
        tvReasoning = view.findViewById(R.id.tvReasoning)
        tvSteps = view.findViewById(R.id.tvSteps)
        scrollConversation = view.findViewById(R.id.scrollConversation)
        tvConversation = view.findViewById(R.id.tvConversation)
        tvSpeaking = view.findViewById(R.id.tvSpeaking)
        tvPatientCount = view.findViewById(R.id.tvPatientCount)
        btnStartTriage = view.findViewById(R.id.btnStartTriage)
        btnNextPatient = view.findViewById(R.id.btnNextPatient)

        btnStartTriage.setOnClickListener { onStartTriageClicked() }
        btnNextPatient.setOnClickListener { viewModel.resetToNextPatient() }

        observeViewModel()
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { state -> renderState(state) }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.patientCount.collect { count ->
                tvPatientCount.text = "Patients triaged: $count"
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.modelReady.collect { ready ->
                btnStartTriage.isEnabled = ready
                if (!ready) tvStatus.text = getString(R.string.status_model_loading)
            }
        }
    }

    private fun renderState(state: TriageUiState) {
        when (state) {
            is TriageUiState.Idle -> {
                tvStatus.text = getString(R.string.status_idle)
                cardResult.visibility = View.INVISIBLE
                scrollConversation.visibility = View.GONE
                tvSpeaking.visibility = View.GONE
                btnNextPatient.visibility = View.GONE
                btnStartTriage.isEnabled = viewModel.modelReady.value
            }
            is TriageUiState.Listening -> {
                tvStatus.text = getString(R.string.status_listening)
                btnStartTriage.isEnabled = false
            }
            is TriageUiState.Transcribing -> {
                tvStatus.text = "Heard: ${state.text}"
            }
            is TriageUiState.Analyzing -> {
                tvStatus.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.ResultReady -> {
                showResult(state.result)
                conversationLog.clear()
                scrollConversation.visibility = View.GONE
                btnNextPatient.visibility = View.VISIBLE
            }
            is TriageUiState.Speaking -> {
                tvStatus.text = getString(R.string.status_speaking)
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking: ${state.stage}"
            }
            is TriageUiState.FollowUpListening -> {
                tvStatus.text = getString(R.string.status_follow_up)
                tvSpeaking.visibility = View.GONE
                scrollConversation.visibility = View.VISIBLE
            }
            is TriageUiState.FollowUpAnalyzing -> {
                tvStatus.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.FollowUpSpeaking -> {
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking answer…"
                conversationLog.append("\nQ: ${state.question}\nA: ${state.answer}\n")
                tvConversation.text = conversationLog.toString()
                scrollConversation.post { scrollConversation.fullScroll(View.FOCUS_DOWN) }
            }
            is TriageUiState.Error -> {
                tvStatus.text = "Error: ${state.message}"
                tvSpeaking.visibility = View.GONE
                btnStartTriage.isEnabled = viewModel.modelReady.value
            }
        }
    }

    private fun showResult(result: TriageResult) {
        cardResult.visibility = View.VISIBLE
        tvTriageCode.text = result.triageCode.name
        tvTriageCode.setTextColor(colorForCode(result.triageCode))
        tvConfidence.text = "${(result.confidence * 100).toInt()}% confidence"
        tvReasoning.text = result.reasoning
        tvSteps.text = result.immediateSteps.mapIndexed { i, s -> "${i + 1}. $s" }.joinToString("\n")
    }

    private fun colorForCode(code: TriageCode): Int = when (code) {
        TriageCode.RED -> requireContext().getColor(R.color.triage_red)
        TriageCode.YELLOW -> requireContext().getColor(R.color.triage_yellow)
        TriageCode.GREEN -> requireContext().getColor(R.color.triage_green)
        TriageCode.BLACK -> requireContext().getColor(R.color.triage_black)
        TriageCode.UNKNOWN -> requireContext().getColor(R.color.triage_unknown)
    }

    private fun onStartTriageClicked() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED
        ) {
            viewModel.startListening()
        } else {
            permissionLauncher.launch(
                arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.SEND_SMS)
            )
        }
    }
}
```

---

### Task A6: Create HistoryFragment stub + fragment_history.xml stub

**Files:**
- Create `android/app/src/main/java/com/gemma/triage/HistoryFragment.kt`
- Create `android/app/src/main/res/layout/fragment_history.xml`

- [ ] **Step 1: Create HistoryFragment.kt stub**

```kotlin
package com.gemma.triage

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment

class HistoryFragment : Fragment() {
    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.fragment_history, container, false)
}
```

- [ ] **Step 2: Create fragment_history.xml stub**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/background_dark"
    android:gravity="center">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="History coming soon"
        android:textColor="@color/on_surface_secondary"
        android:textSize="16sp" />

</LinearLayout>
```

---

### Task A7: Refactor MainActivity.kt to thin shell

**Files:** Modify `android/app/src/main/java/com/gemma/triage/MainActivity.kt`

- [ ] **Step 1: Replace the entire file**

```kotlin
package com.gemma.triage

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.viewpager2.widget.ViewPager2
import com.google.android.material.tabs.TabLayout
import com.google.android.material.tabs.TabLayoutMediator

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val viewPager = findViewById<ViewPager2>(R.id.viewPager)
        val tabIndicator = findViewById<TabLayout>(R.id.tabIndicator)

        viewPager.adapter = TriagePagerAdapter(this)
        viewPager.isUserInputEnabled = true

        TabLayoutMediator(tabIndicator, viewPager) { tab, position ->
            tab.text = if (position == 0) "Triage" else "History"
        }.attach()
    }
}
```

---

### Task A8: Compile check + commit

- [ ] **Step 1: Compile**
```bash
cd android && ./gradlew :app:compileDebugKotlin
```
Expected: `BUILD SUCCESSFUL`

- [ ] **Step 2: Commit**
```bash
cd android && git add -A && git commit -m "feat: refactor MainActivity to ViewPager2 shell with TriageFragment + HistoryFragment"
```

---

## Phase B: Triage Screen Material 3 + Animations

> **Prerequisite:** Phase A must be complete.

### Task B1: Add new strings and colors

**Files:**
- Modify `android/app/src/main/res/values/strings.xml`
- Modify `android/app/src/main/res/values/colors.xml`

- [ ] **Step 1: Replace strings.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Gemma Triage</string>
    <string name="btn_start_triage">Start Triage</string>
    <string name="btn_next_patient">Next Patient</string>
    <string name="status_idle">Ready — tap to begin triage</string>
    <string name="status_listening">Listening…</string>
    <string name="status_analyzing">Analyzing…</string>
    <string name="status_speaking">Speaking result…</string>
    <string name="status_follow_up">Follow-up mode — ask a question</string>
    <string name="status_model_loading">Loading model…</string>
    <string name="label_patients_triaged">Patients triaged: %d</string>
    <string name="label_no_history">No patients triaged yet.</string>
    <string name="label_patients_today">%d patient(s) today</string>
    <string name="label_transcription">Transcription</string>
    <string name="label_steps">Immediate Steps</string>
    <string name="label_sms">SMS Payload</string>
    <string name="label_sms_sent">SMS sent</string>
    <string name="label_sms_pending">Pending</string>
</resources>
```

- [ ] **Step 2: Add `bubble_answer` color to colors.xml**

Add inside `<resources>`:
```xml
    <color name="bubble_answer">#1A2744</color>
```

---

### Task B2: Create shape_pulse_circle.xml

**Files:** Create `android/app/src/main/res/drawable/shape_pulse_circle.xml`

- [ ] **Step 1: Create the file**

```xml
<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="oval">
    <solid android:color="#331565C0" />
</shape>
```

---

### Task B3: Upgrade fragment_triage.xml to Material 3

**Files:** Modify `android/app/src/main/res/layout/fragment_triage.xml`

- [ ] **Step 1: Replace the entire file**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:tools="http://schemas.android.com/tools"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/background_dark"
    android:padding="16dp">

    <com.google.android.material.progressindicator.LinearProgressIndicator
        android:id="@+id/progressIndicator"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:indeterminate="true"
        app:indicatorColor="@color/accent_blue"
        app:trackColor="@color/surface"
        android:visibility="invisible" />

    <TextView
        android:id="@+id/tvStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="@string/status_idle"
        android:textColor="@color/on_surface_secondary"
        android:textSize="14sp"
        android:paddingVertical="8dp" />

    <com.google.android.material.card.MaterialCardView
        android:id="@+id/cardResult"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        app:cardBackgroundColor="@color/surface"
        app:cardCornerRadius="12dp"
        app:cardElevation="4dp"
        app:strokeWidth="3dp"
        app:strokeColor="@color/surface"
        android:visibility="invisible">

        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="match_parent"
            android:orientation="vertical"
            android:gravity="center"
            android:padding="16dp">

            <TextView
                android:id="@+id/tvTriageCode"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="64sp"
                android:textStyle="bold"
                android:textColor="@color/on_surface"
                tools:text="RED" />

            <TextView
                android:id="@+id/tvConfidence"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="18sp"
                android:textColor="@color/on_surface_secondary"
                android:paddingTop="4dp"
                tools:text="97% confidence" />

            <TextView
                android:id="@+id/tvReasoning"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:textColor="@color/on_surface_secondary"
                android:paddingTop="12dp"
                tools:text="Breathing irregular, BP dropping" />

            <TextView
                android:id="@+id/tvSteps"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:textColor="@color/on_surface"
                android:paddingTop="12dp"
                tools:text="1. Secure airway" />
        </LinearLayout>
    </com.google.android.material.card.MaterialCardView>

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/rvConversation"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:visibility="gone"
        android:clipToPadding="false"
        android:padding="4dp" />

    <TextView
        android:id="@+id/tvSpeaking"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="@string/status_speaking"
        android:textColor="@color/accent_blue"
        android:textSize="14sp"
        android:paddingVertical="8dp"
        android:visibility="gone" />

    <TextView
        android:id="@+id/tvPatientCount"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textColor="@color/on_surface_secondary"
        android:textSize="12sp"
        android:paddingBottom="8dp"
        tools:text="Patients triaged: 0" />

    <com.google.android.material.button.MaterialButton
        android:id="@+id/btnNextPatient"
        style="@style/Widget.Material3.Button.OutlinedButton"
        android:layout_width="match_parent"
        android:layout_height="48dp"
        android:text="@string/btn_next_patient"
        android:textSize="14sp"
        android:visibility="gone"
        android:layout_marginBottom="8dp" />

    <FrameLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:gravity="center">

        <View
            android:id="@+id/viewPulse"
            android:layout_width="80dp"
            android:layout_height="80dp"
            android:layout_gravity="center"
            android:background="@drawable/shape_pulse_circle"
            android:visibility="invisible" />

        <com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton
            android:id="@+id/fabMic"
            android:layout_width="match_parent"
            android:layout_height="56dp"
            android:text="@string/btn_start_triage"
            android:textSize="16sp"
            android:textColor="@color/on_surface"
            app:backgroundTint="@color/accent_blue" />
    </FrameLayout>

</LinearLayout>
```

---

### Task B4: Create ConversationBubbleAdapter and item layout

**Files:**
- Create `android/app/src/main/java/com/gemma/triage/ConversationBubbleAdapter.kt`
- Create `android/app/src/main/res/layout/item_conversation_bubble.xml`

- [ ] **Step 1: Create item_conversation_bubble.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:paddingVertical="4dp"
    android:paddingHorizontal="4dp">

    <com.google.android.material.card.MaterialCardView
        android:id="@+id/cardBubble"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_gravity="start"
        app:cardCornerRadius="12dp"
        app:cardElevation="2dp"
        app:cardMaxWidth="300dp">

        <TextView
            android:id="@+id/tvBubbleText"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:padding="10dp"
            android:textSize="14sp"
            android:textColor="@color/on_surface" />

    </com.google.android.material.card.MaterialCardView>

</FrameLayout>
```

- [ ] **Step 2: Create ConversationBubbleAdapter.kt**

```kotlin
package com.gemma.triage

import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView

data class ConversationBubble(val text: String, val isQuestion: Boolean)

class ConversationBubbleAdapter : RecyclerView.Adapter<ConversationBubbleAdapter.ViewHolder>() {

    private var bubbles: List<ConversationBubble> = emptyList()

    fun submitList(list: List<ConversationBubble>) {
        bubbles = list
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_conversation_bubble, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) =
        holder.bind(bubbles[position])

    override fun getItemCount() = bubbles.size

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val card: MaterialCardView = itemView.findViewById(R.id.cardBubble)
        private val tvText: TextView = itemView.findViewById(R.id.tvBubbleText)

        fun bind(bubble: ConversationBubble) {
            tvText.text = bubble.text
            val ctx = itemView.context
            val params = card.layoutParams as FrameLayout.LayoutParams
            if (bubble.isQuestion) {
                params.gravity = Gravity.START
                card.setCardBackgroundColor(ContextCompat.getColor(ctx, R.color.surface))
            } else {
                params.gravity = Gravity.END
                card.setCardBackgroundColor(ContextCompat.getColor(ctx, R.color.bubble_answer))
            }
            card.layoutParams = params
        }
    }
}
```

---

### Task B5: Upgrade TriageFragment.kt with Material 3 bindings and animations

**Files:** Modify `android/app/src/main/java/com/gemma/triage/TriageFragment.kt`

- [ ] **Step 1: Replace the entire file**

```kotlin
package com.gemma.triage

import android.Manifest
import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.animation.DecelerateInterpolator
import android.view.animation.OvershootInterpolator
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.google.android.material.button.MaterialButton
import com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.viewmodel.TriageUiState
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch

class TriageFragment : Fragment() {

    private val viewModel: TriageViewModel by activityViewModels()

    private lateinit var progressIndicator: LinearProgressIndicator
    private lateinit var tvStatus: TextView
    private lateinit var cardResult: MaterialCardView
    private lateinit var tvTriageCode: TextView
    private lateinit var tvConfidence: TextView
    private lateinit var tvReasoning: TextView
    private lateinit var tvSteps: TextView
    private lateinit var rvConversation: RecyclerView
    private lateinit var tvSpeaking: TextView
    private lateinit var tvPatientCount: TextView
    private lateinit var btnNextPatient: MaterialButton
    private lateinit var fabMic: ExtendedFloatingActionButton
    private lateinit var viewPulse: View

    private val bubbleAdapter = ConversationBubbleAdapter()
    private val conversationBubbles = mutableListOf<ConversationBubble>()
    private var pulseAnimator: AnimatorSet? = null

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants[Manifest.permission.RECORD_AUDIO] == true) {
            viewModel.startListening()
        } else {
            tvStatus.text = "Microphone permission required"
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.fragment_triage, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        progressIndicator = view.findViewById(R.id.progressIndicator)
        tvStatus = view.findViewById(R.id.tvStatus)
        cardResult = view.findViewById(R.id.cardResult)
        tvTriageCode = view.findViewById(R.id.tvTriageCode)
        tvConfidence = view.findViewById(R.id.tvConfidence)
        tvReasoning = view.findViewById(R.id.tvReasoning)
        tvSteps = view.findViewById(R.id.tvSteps)
        rvConversation = view.findViewById(R.id.rvConversation)
        tvSpeaking = view.findViewById(R.id.tvSpeaking)
        tvPatientCount = view.findViewById(R.id.tvPatientCount)
        btnNextPatient = view.findViewById(R.id.btnNextPatient)
        fabMic = view.findViewById(R.id.fabMic)
        viewPulse = view.findViewById(R.id.viewPulse)

        rvConversation.layoutManager = LinearLayoutManager(requireContext()).also { it.stackFromEnd = true }
        rvConversation.adapter = bubbleAdapter

        fabMic.setOnClickListener { onMicClicked() }
        btnNextPatient.setOnClickListener {
            slideOutNextPatient()
            viewModel.resetToNextPatient()
        }

        observeViewModel()
    }

    private fun observeViewModel() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.uiState.collect { renderState(it) }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.patientCount.collect { count ->
                tvPatientCount.text = getString(R.string.label_patients_triaged, count)
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.modelReady.collect { ready ->
                fabMic.isEnabled = ready
                if (!ready) tvStatus.text = getString(R.string.status_model_loading)
            }
        }
    }

    private fun renderState(state: TriageUiState) {
        when (state) {
            is TriageUiState.Idle -> {
                progressIndicator.visibility = View.INVISIBLE
                tvStatus.text = getString(R.string.status_idle)
                cardResult.visibility = View.INVISIBLE
                rvConversation.visibility = View.GONE
                tvSpeaking.visibility = View.GONE
                slideOutNextPatient()
                stopPulse()
                fabMic.text = getString(R.string.btn_start_triage)
                fabMic.isEnabled = viewModel.modelReady.value
            }
            is TriageUiState.Listening -> {
                progressIndicator.visibility = View.INVISIBLE
                tvStatus.text = getString(R.string.status_listening)
                fabMic.text = getString(R.string.status_listening)
                fabMic.isEnabled = false
                startPulse()
            }
            is TriageUiState.Transcribing -> {
                stopPulse()
                tvStatus.text = "Heard: ${state.text}"
                progressIndicator.visibility = View.VISIBLE
            }
            is TriageUiState.Analyzing -> {
                progressIndicator.visibility = View.VISIBLE
                tvStatus.text = getString(R.string.status_analyzing)
                fabMic.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.ResultReady -> {
                progressIndicator.visibility = View.INVISIBLE
                showResult(state.result)
                conversationBubbles.clear()
                bubbleAdapter.submitList(emptyList())
                rvConversation.visibility = View.GONE
                slideInNextPatient()
                fabMic.text = getString(R.string.btn_start_triage)
                fabMic.isEnabled = false
            }
            is TriageUiState.Speaking -> {
                tvStatus.text = getString(R.string.status_speaking)
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking: ${state.stage}"
                fabMic.text = "Speaking…"
            }
            is TriageUiState.FollowUpListening -> {
                progressIndicator.visibility = View.INVISIBLE
                tvStatus.text = getString(R.string.status_follow_up)
                tvSpeaking.visibility = View.GONE
                rvConversation.visibility = View.VISIBLE
                fabMic.text = "Ask a question…"
                startPulse()
            }
            is TriageUiState.FollowUpAnalyzing -> {
                stopPulse()
                progressIndicator.visibility = View.VISIBLE
                tvStatus.text = getString(R.string.status_analyzing)
            }
            is TriageUiState.FollowUpSpeaking -> {
                progressIndicator.visibility = View.INVISIBLE
                tvSpeaking.visibility = View.VISIBLE
                tvSpeaking.text = "Speaking answer…"
                conversationBubbles.add(ConversationBubble(state.question, isQuestion = true))
                conversationBubbles.add(ConversationBubble(state.answer, isQuestion = false))
                bubbleAdapter.submitList(conversationBubbles.toList())
                rvConversation.scrollToPosition(bubbleAdapter.itemCount - 1)
            }
            is TriageUiState.Error -> {
                progressIndicator.visibility = View.INVISIBLE
                stopPulse()
                tvStatus.text = "Error: ${state.message}"
                tvSpeaking.visibility = View.GONE
                fabMic.text = getString(R.string.btn_start_triage)
                fabMic.isEnabled = viewModel.modelReady.value
            }
        }
    }

    private fun showResult(result: TriageResult) {
        val triageColor = colorForCode(result.triageCode)
        cardResult.strokeColor = triageColor
        cardResult.visibility = View.VISIBLE

        tvTriageCode.text = result.triageCode.name
        tvTriageCode.setTextColor(triageColor)
        tvConfidence.text = "${(result.confidence * 100).toInt()}% confidence"
        tvReasoning.text = result.reasoning
        tvSteps.text = result.immediateSteps.mapIndexed { i, s -> "${i + 1}. $s" }.joinToString("\n")

        // Scale-up triage code
        tvTriageCode.scaleX = 0f
        tvTriageCode.scaleY = 0f
        tvTriageCode.animate()
            .scaleX(1f).scaleY(1f)
            .setDuration(400)
            .setInterpolator(OvershootInterpolator(2f))
            .start()

        // Card background flash
        val surface = ContextCompat.getColor(requireContext(), R.color.surface)
        val tinted = tintedSurface(result.triageCode)
        ValueAnimator.ofArgb(surface, tinted, surface).apply {
            duration = 800
            addUpdateListener { cardResult.setCardBackgroundColor(it.animatedValue as Int) }
            start()
        }
    }

    private fun tintedSurface(code: TriageCode): Int = when (code) {
        TriageCode.RED    -> 0xFF3A1C1C.toInt()
        TriageCode.YELLOW -> 0xFF3A3118.toInt()
        TriageCode.GREEN  -> 0xFF1C3A1E.toInt()
        TriageCode.BLACK  -> 0xFF2A2A2A.toInt()
        TriageCode.UNKNOWN -> 0xFF282828.toInt()
    }

    private fun colorForCode(code: TriageCode): Int = when (code) {
        TriageCode.RED -> requireContext().getColor(R.color.triage_red)
        TriageCode.YELLOW -> requireContext().getColor(R.color.triage_yellow)
        TriageCode.GREEN -> requireContext().getColor(R.color.triage_green)
        TriageCode.BLACK -> requireContext().getColor(R.color.triage_black)
        TriageCode.UNKNOWN -> requireContext().getColor(R.color.triage_unknown)
    }

    private fun startPulse() {
        viewPulse.visibility = View.VISIBLE
        viewPulse.scaleX = 1f; viewPulse.scaleY = 1f; viewPulse.alpha = 0.6f
        val sx = ObjectAnimator.ofFloat(viewPulse, "scaleX", 1f, 2.5f)
        val sy = ObjectAnimator.ofFloat(viewPulse, "scaleY", 1f, 2.5f)
        val al = ObjectAnimator.ofFloat(viewPulse, "alpha", 0.6f, 0f)
        pulseAnimator = AnimatorSet().apply {
            playTogether(sx, sy, al)
            duration = 1000
            addListener(object : android.animation.AnimatorListenerAdapter() {
                override fun onAnimationEnd(a: android.animation.Animator) {
                    if (viewPulse.visibility == View.VISIBLE) {
                        viewPulse.scaleX = 1f; viewPulse.scaleY = 1f; viewPulse.alpha = 0.6f
                        start()
                    }
                }
            })
            start()
        }
    }

    private fun stopPulse() {
        pulseAnimator?.cancel()
        pulseAnimator = null
        viewPulse.visibility = View.INVISIBLE
    }

    private fun slideInNextPatient() {
        btnNextPatient.visibility = View.VISIBLE
        btnNextPatient.translationY = 200f
        btnNextPatient.animate()
            .translationY(0f)
            .setDuration(300)
            .setInterpolator(DecelerateInterpolator())
            .start()
    }

    private fun slideOutNextPatient() {
        if (btnNextPatient.visibility == View.VISIBLE) {
            btnNextPatient.animate()
                .translationY(200f)
                .setDuration(200)
                .withEndAction { btnNextPatient.visibility = View.GONE }
                .start()
        }
    }

    private fun onMicClicked() {
        if (ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED) {
            viewModel.startListening()
        } else {
            permissionLauncher.launch(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.SEND_SMS))
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        pulseAnimator?.cancel()
    }
}
```

---

### Task B6: Compile check + feature doc + commit

- [ ] **Step 1: Compile**
```bash
cd android && ./gradlew :app:compileDebugKotlin
```
Expected: `BUILD SUCCESSFUL`

- [ ] **Step 2: Create feature doc** at `docs/features/ui-material3-overhaul.md`

```markdown
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
```

- [ ] **Step 3: Commit**
```bash
cd android && git add -A && git commit -m "feat: upgrade triage screen to Material 3 with pulse, flash, and bubble animations"
```

---

## Phase C: History Screen

> **Prerequisite:** Phase A must be complete. Can run in parallel with Phase B.

### Task C1: Write failing unit test for HistoryExpandState

**Files:**
- Create `android/app/src/test/java/com/gemma/triage/HistoryExpandStateTest.kt`
- Create `android/app/src/main/java/com/gemma/triage/HistoryExpandState.kt` (empty stub)

- [ ] **Step 1: Create HistoryExpandState.kt stub**

```kotlin
package com.gemma.triage

class HistoryExpandState {
    var expandedPosition: Int = -1
}
```

- [ ] **Step 2: Create HistoryExpandStateTest.kt**

```kotlin
package com.gemma.triage

import org.junit.Assert.assertEquals
import org.junit.Test

class HistoryExpandStateTest {

    @Test
    fun `initial state has no expanded item`() {
        val state = HistoryExpandState()
        assertEquals(-1, state.expandedPosition)
    }

    @Test
    fun `toggle expands an item`() {
        val state = HistoryExpandState()
        state.toggle(2)
        assertEquals(2, state.expandedPosition)
    }

    @Test
    fun `toggle same item collapses it`() {
        val state = HistoryExpandState()
        state.toggle(2)
        state.toggle(2)
        assertEquals(-1, state.expandedPosition)
    }

    @Test
    fun `toggle different item returns old collapsed position`() {
        val state = HistoryExpandState()
        state.toggle(2)
        val collapsed = state.toggle(5)
        assertEquals(5, state.expandedPosition)
        assertEquals(2, collapsed)
    }

    @Test
    fun `toggle when nothing expanded returns -1 as collapsed`() {
        val state = HistoryExpandState()
        val collapsed = state.toggle(3)
        assertEquals(-1, collapsed)
    }
}
```

- [ ] **Step 3: Run test — expect FAIL**
```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.HistoryExpandStateTest" 2>&1 | tail -20
```
Expected: `FAILED` (method `toggle` doesn't exist yet)

---

### Task C2: Implement HistoryExpandState + verify tests pass

**Files:** Modify `android/app/src/main/java/com/gemma/triage/HistoryExpandState.kt`

- [ ] **Step 1: Implement toggle()**

```kotlin
package com.gemma.triage

class HistoryExpandState {
    var expandedPosition: Int = -1

    fun toggle(position: Int): Int {
        val old = expandedPosition
        expandedPosition = if (old == position) -1 else position
        return old
    }
}
```

- [ ] **Step 2: Run tests — expect PASS**
```bash
cd android && ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.HistoryExpandStateTest"
```
Expected: `BUILD SUCCESSFUL`, 5 tests passed.

---

### Task C3: Update TriageRecord and DatabaseHelper

**Files:**
- Modify `android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt`
- Modify `android/app/src/main/java/com/gemma/triage/storage/DatabaseHelper.kt`

- [ ] **Step 1: Add `immediateSteps` field to TriageRecord**

Replace `android/app/src/main/java/com/gemma/triage/storage/models/TriageRecord.kt`:

```kotlin
package com.gemma.triage.storage.models

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "triage_records")
data class TriageRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val timestamp: Long,
    val triageCode: String,
    val confidence: Double,
    val transcription: String,
    val immediateSteps: String,
    val smsPayload: String,
    val isTransmitted: Boolean = false
)
```

- [ ] **Step 2: Bump Room version to 2 with fallbackToDestructiveMigration**

In `android/app/src/main/java/com/gemma/triage/storage/DatabaseHelper.kt`, change:
- Line 21: `@Database(entities = [TriageRecord::class], version = 1)` → `version = 2`
- In the `databaseBuilder` chain, add `.fallbackToDestructiveMigration()` before `.build()`

Full replacement:
```kotlin
package com.gemma.triage.storage

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import com.gemma.triage.storage.models.TriageRecord

@Dao
interface TriageDao {
    @Insert
    suspend fun insert(record: TriageRecord)

    @Query("SELECT * FROM triage_records ORDER BY timestamp DESC")
    suspend fun getAllRecords(): List<TriageRecord>
}

@Database(entities = [TriageRecord::class], version = 2)
abstract class AppDatabase : RoomDatabase() {
    abstract fun triageDao(): TriageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "triage_database"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
```

---

### Task C4: Update TriageOutputManager to store immediateSteps

**Files:** Modify `android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt`

- [ ] **Step 1: Pass immediateSteps when building TriageRecord**

In `process()`, update the record construction (lines 21–27). Replace the `process` function:

```kotlin
fun process(result: TriageResult, transcription: String) {
    val record = TriageRecord(
        timestamp = System.currentTimeMillis(),
        triageCode = result.triageCode.name,
        confidence = result.confidence,
        transcription = transcription,
        immediateSteps = result.immediateSteps.joinToString("\n"),
        smsPayload = SMSFormatter.formatForSMS(result),
        isTransmitted = false
    )
    dbWriter(record)
    queueManager.enqueue(result)
    queueManager.processQueue()
}
```

---

### Task C5: Add history StateFlow to TriageViewModel

**Files:** Modify `android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt`

- [ ] **Step 1: Replace the full file**

```kotlin
package com.gemma.triage.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.gemma.triage.audio.STTState
import com.gemma.triage.audio.SpeechToTextManager
import com.gemma.triage.audio.TTSState
import com.gemma.triage.audio.TextToSpeechManager
import com.gemma.triage.inference.ConversationManager
import com.gemma.triage.inference.GemmaInferenceEngine
import com.gemma.triage.output.TriageOutputManager
import com.gemma.triage.storage.AppDatabase
import com.gemma.triage.storage.models.TriageRecord
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.io.File

class TriageViewModel(application: Application) : AndroidViewModel(application) {

    private val context = application.applicationContext
    private val inferenceEngine = GemmaInferenceEngine(context)
    private val sttManager = SpeechToTextManager(context)
    private val ttsManager = TextToSpeechManager(context)
    private val conversationManager = ConversationManager()
    private val outputManager = TriageOutputManager.create(context)
    private val db = AppDatabase.getDatabase(context)

    private val _uiState = MutableStateFlow<TriageUiState>(TriageUiState.Idle)
    val uiState: StateFlow<TriageUiState> = _uiState

    private val _patientCount = MutableStateFlow(0)
    val patientCount: StateFlow<Int> = _patientCount

    private val _modelReady = MutableStateFlow(false)
    val modelReady: StateFlow<Boolean> = _modelReady

    private val _history = MutableStateFlow<List<TriageRecord>>(emptyList())
    val history: StateFlow<List<TriageRecord>> = _history

    private var inFollowUpMode = false
    private var lastQuestion = ""

    init {
        observeSTT()
        observeTTS()
        loadModelAsync()
        loadHistory()
    }

    private fun loadHistory() {
        viewModelScope.launch(Dispatchers.IO) {
            _history.value = db.triageDao().getAllRecords()
        }
    }

    private fun loadModelAsync() {
        viewModelScope.launch {
            try {
                val modelFile = File(context.filesDir, "gemma2-2b-it-cpu-int8.task")
                if (modelFile.exists()) {
                    inferenceEngine.loadModel(modelFile.absolutePath)
                    _modelReady.value = true
                } else {
                    _uiState.value = TriageUiState.Error("Model not found. Run setup_model.py first.")
                }
            } catch (e: Exception) {
                _uiState.value = TriageUiState.Error("Model load failed: ${e.message}")
            }
        }
    }

    private fun observeSTT() {
        viewModelScope.launch {
            sttManager.state.collectLatest { state ->
                when (state) {
                    is STTState.Listening -> {
                        _uiState.value = if (inFollowUpMode)
                            TriageUiState.FollowUpListening
                        else
                            TriageUiState.Listening
                    }
                    is STTState.Result -> {
                        val text = state.text
                        if (text.isBlank()) {
                            _uiState.value = TriageUiState.Error("No speech detected — try again")
                            return@collectLatest
                        }
                        if (inFollowUpMode) {
                            if (conversationManager.isNextPatientCommand(text)) {
                                resetToNextPatient()
                            } else {
                                runFollowUpInference(text)
                            }
                        } else {
                            _uiState.value = TriageUiState.Transcribing(text)
                            runInitialInference(text)
                        }
                    }
                    is STTState.Error -> _uiState.value = TriageUiState.Error(state.message)
                    is STTState.Idle -> { /* no-op */ }
                }
            }
        }
    }

    private fun observeTTS() {
        viewModelScope.launch {
            ttsManager.state.collectLatest { state ->
                when (state) {
                    is TTSState.Done -> {
                        inFollowUpMode = true
                        sttManager.startListening()
                    }
                    is TTSState.Speaking -> {
                        _uiState.value = TriageUiState.Speaking(state.stage)
                    }
                    else -> { /* no-op */ }
                }
            }
        }
    }

    fun startListening() {
        if (!_modelReady.value) {
            _uiState.value = TriageUiState.Error("Model not ready yet.")
            return
        }
        inFollowUpMode = false
        conversationManager.clear()
        sttManager.startListening()
    }

    fun stopListening() = sttManager.stopListening()

    private fun runInitialInference(transcription: String) {
        viewModelScope.launch {
            _uiState.value = TriageUiState.Analyzing
            try {
                val result = inferenceEngine.runTriageInference(transcription)
                _patientCount.value += 1
                outputManager.process(result, transcription)
                conversationManager.startNewPatient(transcription, result)
                _uiState.value = TriageUiState.ResultReady(result, transcription)
                ttsManager.speakTriageResult(result)
                loadHistory()
            } catch (e: Exception) {
                _uiState.value = TriageUiState.Error("Inference failed: ${e.message}")
            }
        }
    }

    private fun runFollowUpInference(question: String) {
        lastQuestion = question
        conversationManager.addTurn("user", question)
        viewModelScope.launch {
            _uiState.value = TriageUiState.FollowUpAnalyzing
            try {
                val prompt = conversationManager.buildFollowUpPrompt(question)
                val answer = inferenceEngine.runFollowUpInference(prompt)
                conversationManager.addTurn("model", answer)
                _uiState.value = TriageUiState.FollowUpSpeaking(question, answer)
                ttsManager.speakFollowUpAnswer(answer)
            } catch (e: Exception) {
                _uiState.value = TriageUiState.Error("Follow-up failed: ${e.message}")
            }
        }
    }

    fun resetToNextPatient() {
        ttsManager.stop()
        inFollowUpMode = false
        conversationManager.clear()
        _uiState.value = TriageUiState.Idle
        ttsManager.speak("Ready for next patient.", "READY")
    }

    override fun onCleared() {
        super.onCleared()
        inferenceEngine.release()
        sttManager.destroy()
        ttsManager.shutdown()
    }
}
```

---

### Task C6: Create item_history_record.xml

**Files:** Create `android/app/src/main/res/layout/item_history_record.xml`

- [ ] **Step 1: Create the file**

```xml
<?xml version="1.0" encoding="utf-8"?>
<com.google.android.material.card.MaterialCardView
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:layout_marginHorizontal="8dp"
    android:layout_marginVertical="4dp"
    app:cardCornerRadius="10dp"
    app:cardBackgroundColor="@color/surface"
    app:cardElevation="2dp"
    app:strokeWidth="1dp"
    app:strokeColor="#2A2A2A">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        android:padding="12dp">

        <!-- Collapsed: always visible -->
        <LinearLayout
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="horizontal"
            android:gravity="center_vertical">

            <com.google.android.material.chip.Chip
                android:id="@+id/chipCode"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textColor="@color/on_surface"
                android:textStyle="bold"
                app:chipMinHeight="28dp"
                style="@style/Widget.Material3.Chip.Assist" />

            <TextView
                android:id="@+id/tvTimestamp"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_weight="1"
                android:layout_marginStart="8dp"
                android:textSize="13sp"
                android:textColor="@color/on_surface_secondary" />

            <TextView
                android:id="@+id/tvConfidenceSmall"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="12sp"
                android:textColor="@color/on_surface_secondary" />

        </LinearLayout>

        <TextView
            android:id="@+id/tvTranscriptionPreview"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:maxLines="1"
            android:ellipsize="end"
            android:textSize="13sp"
            android:textColor="@color/on_surface_secondary"
            android:paddingTop="6dp" />

        <!-- Expanded: hidden by default -->
        <LinearLayout
            android:id="@+id/layoutExpanded"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical"
            android:visibility="gone">

            <View
                android:layout_width="match_parent"
                android:layout_height="1dp"
                android:background="#2A2A2A"
                android:layout_marginVertical="10dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="@string/label_transcription"
                android:textSize="11sp"
                android:textColor="@color/on_surface_secondary"
                android:textAllCaps="true"
                android:letterSpacing="0.08" />

            <TextView
                android:id="@+id/tvTranscriptionFull"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:textColor="@color/on_surface"
                android:paddingTop="4dp"
                android:paddingBottom="10dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="@string/label_steps"
                android:textSize="11sp"
                android:textColor="@color/on_surface_secondary"
                android:textAllCaps="true"
                android:letterSpacing="0.08" />

            <TextView
                android:id="@+id/tvStepsExpanded"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:textSize="14sp"
                android:textColor="@color/on_surface"
                android:paddingTop="4dp"
                android:paddingBottom="10dp" />

            <TextView
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="@string/label_sms"
                android:textSize="11sp"
                android:textColor="@color/on_surface_secondary"
                android:textAllCaps="true"
                android:letterSpacing="0.08" />

            <TextView
                android:id="@+id/tvSmsPayload"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:textSize="12sp"
                android:textColor="@color/on_surface_secondary"
                android:fontFamily="monospace"
                android:paddingTop="4dp"
                android:paddingBottom="10dp" />

            <com.google.android.material.chip.Chip
                android:id="@+id/chipTransmitted"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:textSize="12sp"
                style="@style/Widget.Material3.Chip.Assist" />

        </LinearLayout>

    </LinearLayout>

</com.google.android.material.card.MaterialCardView>
```

---

### Task C7: Create HistoryAdapter.kt

**Files:** Create `android/app/src/main/java/com/gemma/triage/HistoryAdapter.kt`

- [ ] **Step 1: Create the file**

```kotlin
package com.gemma.triage

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.transition.AutoTransition
import androidx.transition.TransitionManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.google.android.material.chip.Chip
import com.gemma.triage.storage.models.TriageRecord
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class HistoryAdapter : RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {

    private var records: List<TriageRecord> = emptyList()
    private val expandState = HistoryExpandState()
    private val dateFormat = SimpleDateFormat("MMM d · HH:mm", Locale.getDefault())

    fun submitList(newRecords: List<TriageRecord>) {
        records = newRecords
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_history_record, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(records[position], position == expandState.expandedPosition) { clickedPos ->
            val old = expandState.toggle(clickedPos)
            if (old != -1 && old != clickedPos) notifyItemChanged(old)
            notifyItemChanged(clickedPos)
        }
    }

    override fun getItemCount() = records.size

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val card: MaterialCardView = itemView as MaterialCardView
        private val chipCode: Chip = itemView.findViewById(R.id.chipCode)
        private val tvTimestamp: TextView = itemView.findViewById(R.id.tvTimestamp)
        private val tvConfidenceSmall: TextView = itemView.findViewById(R.id.tvConfidenceSmall)
        private val tvTranscriptionPreview: TextView = itemView.findViewById(R.id.tvTranscriptionPreview)
        private val layoutExpanded: LinearLayout = itemView.findViewById(R.id.layoutExpanded)
        private val tvTranscriptionFull: TextView = itemView.findViewById(R.id.tvTranscriptionFull)
        private val tvStepsExpanded: TextView = itemView.findViewById(R.id.tvStepsExpanded)
        private val tvSmsPayload: TextView = itemView.findViewById(R.id.tvSmsPayload)
        private val chipTransmitted: Chip = itemView.findViewById(R.id.chipTransmitted)

        fun bind(record: TriageRecord, isExpanded: Boolean, onToggle: (Int) -> Unit) {
            chipCode.text = record.triageCode
            chipCode.chipBackgroundColor = android.content.res.ColorStateList.valueOf(codeColor(record.triageCode))
            tvTimestamp.text = dateFormat.format(Date(record.timestamp))
            tvConfidenceSmall.text = "${(record.confidence * 100).toInt()}%"
            tvTranscriptionPreview.text = record.transcription

            tvTranscriptionFull.text = record.transcription
            tvStepsExpanded.text = record.immediateSteps
            tvSmsPayload.text = record.smsPayload

            if (record.isTransmitted) {
                chipTransmitted.text = itemView.context.getString(R.string.label_sms_sent)
                chipTransmitted.chipBackgroundColor = android.content.res.ColorStateList.valueOf(0xFF1B5E20.toInt())
            } else {
                chipTransmitted.text = itemView.context.getString(R.string.label_sms_pending)
                chipTransmitted.chipBackgroundColor = android.content.res.ColorStateList.valueOf(0xFF424242.toInt())
            }

            layoutExpanded.visibility = if (isExpanded) View.VISIBLE else View.GONE

            card.setOnClickListener {
                val pos = adapterPosition
                if (pos == RecyclerView.NO_POSITION) return@setOnClickListener
                val rvParent = card.parent as? ViewGroup ?: return@setOnClickListener
                TransitionManager.beginDelayedTransition(rvParent, AutoTransition().apply { duration = 200 })
                onToggle(pos)
            }
        }

        private fun codeColor(code: String): Int = when (code) {
            "RED"    -> 0xFFD32F2F.toInt()
            "YELLOW" -> 0xFFF9A825.toInt()
            "GREEN"  -> 0xFF388E3C.toInt()
            "BLACK"  -> 0xFF424242.toInt()
            else     -> 0xFF757575.toInt()
        }
    }
}
```

---

### Task C8: Implement HistoryFragment and fragment_history.xml

**Files:**
- Modify `android/app/src/main/res/layout/fragment_history.xml`
- Modify `android/app/src/main/java/com/gemma/triage/HistoryFragment.kt`

- [ ] **Step 1: Replace fragment_history.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="@color/background_dark">

    <TextView
        android:id="@+id/tvHistoryHeader"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:padding="16dp"
        android:paddingBottom="8dp"
        android:textSize="13sp"
        android:textColor="@color/on_surface_secondary"
        android:textAllCaps="true"
        android:letterSpacing="0.08"
        android:text="@string/label_patients_today" />

    <TextView
        android:id="@+id/tvEmpty"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:gravity="center"
        android:text="@string/label_no_history"
        android:textSize="16sp"
        android:textColor="@color/on_surface_secondary"
        android:visibility="gone" />

    <androidx.recyclerview.widget.RecyclerView
        android:id="@+id/rvHistory"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:clipToPadding="false"
        android:paddingBottom="8dp" />

</LinearLayout>
```

- [ ] **Step 2: Replace HistoryFragment.kt**

```kotlin
package com.gemma.triage

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.gemma.triage.viewmodel.TriageViewModel
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

class HistoryFragment : Fragment() {

    private val viewModel: TriageViewModel by activityViewModels()
    private val adapter = HistoryAdapter()
    private val dayFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.fragment_history, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val rvHistory = view.findViewById<RecyclerView>(R.id.rvHistory)
        val tvEmpty = view.findViewById<TextView>(R.id.tvEmpty)
        val tvHeader = view.findViewById<TextView>(R.id.tvHistoryHeader)

        rvHistory.layoutManager = LinearLayoutManager(requireContext())
        rvHistory.adapter = adapter

        viewLifecycleOwner.lifecycleScope.launch {
            viewModel.history.collect { records ->
                adapter.submitList(records)
                if (records.isEmpty()) {
                    tvEmpty.visibility = View.VISIBLE
                    rvHistory.visibility = View.GONE
                    tvHeader.text = getString(R.string.label_patients_today, 0)
                } else {
                    tvEmpty.visibility = View.GONE
                    rvHistory.visibility = View.VISIBLE
                    val today = dayFormat.format(Date())
                    val todayCount = records.count { dayFormat.format(Date(it.timestamp)) == today }
                    tvHeader.text = getString(R.string.label_patients_today, todayCount)
                }
            }
        }
    }
}
```

---

### Task C9: Compile check + feature doc + commit

- [ ] **Step 1: Run all unit tests**
```bash
cd android && ./gradlew :app:testDebugUnitTest
```
Expected: `BUILD SUCCESSFUL`

- [ ] **Step 2: Compile**
```bash
cd android && ./gradlew :app:compileDebugKotlin
```
Expected: `BUILD SUCCESSFUL`

- [ ] **Step 3: Create feature doc** at `docs/features/patient-history-screen.md`

```markdown
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
```

- [ ] **Step 4: Commit**
```bash
cd android && git add -A && git commit -m "feat: add patient history screen with expandable cards and TriageRecord immediateSteps field"
```

---

## Phase D: App Icon

> **Independent** — can run at any time, in parallel with any other phase.

### Task D1: Create launcher icon foreground vector

**Files:** Create `android/app/src/main/res/drawable/ic_launcher_foreground.xml`

- [ ] **Step 1: Create the file**

```xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">

    <!-- Triage arc: RED segment -->
    <path
        android:pathData="M54,72 A26,26 0 0,1 31.4,59"
        android:strokeColor="#D32F2F"
        android:strokeWidth="5"
        android:strokeLineCap="round"
        android:fillColor="@android:color/transparent" />

    <!-- Triage arc: YELLOW segment -->
    <path
        android:pathData="M31.4,59 A26,26 0 0,1 54,46"
        android:strokeColor="#F9A825"
        android:strokeWidth="5"
        android:strokeLineCap="round"
        android:fillColor="@android:color/transparent" />

    <!-- Triage arc: GREEN segment -->
    <path
        android:pathData="M54,46 A26,26 0 0,1 76.6,59"
        android:strokeColor="#388E3C"
        android:strokeWidth="5"
        android:strokeLineCap="round"
        android:fillColor="@android:color/transparent" />

    <!-- Medical cross: vertical bar -->
    <rect
        android:x="49"
        android:y="34"
        android:width="10"
        android:height="40"
        android:fillColor="#FFFFFF" />

    <!-- Medical cross: horizontal bar -->
    <rect
        android:x="34"
        android:y="49"
        android:width="40"
        android:height="10"
        android:fillColor="#FFFFFF" />

</vector>
```

---

### Task D2: Create background and monochrome drawables

**Files:**
- Create `android/app/src/main/res/drawable/ic_launcher_background.xml`
- Create `android/app/src/main/res/drawable/ic_launcher_monochrome.xml`

- [ ] **Step 1: Create ic_launcher_background.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#0A1628"
        android:pathData="M0,0h108v108h-108z" />
</vector>
```

- [ ] **Step 2: Create ic_launcher_monochrome.xml** (cross only, no arc, single tone)

```xml
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">

    <!-- Vertical bar -->
    <rect
        android:x="49"
        android:y="30"
        android:width="10"
        android:height="48"
        android:fillColor="#FFFFFF" />

    <!-- Horizontal bar -->
    <rect
        android:x="30"
        android:y="49"
        android:width="48"
        android:height="10"
        android:fillColor="#FFFFFF" />

</vector>
```

---

### Task D3: Create adaptive icon manifest XMLs

**Files:**
- Create directory `android/app/src/main/res/mipmap-anydpi-v26/`
- Create `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`
- Create `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml`

- [ ] **Step 1: Create the directory**
```bash
mkdir -p android/app/src/main/res/mipmap-anydpi-v26
```

- [ ] **Step 2: Create ic_launcher.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_monochrome" />
</adaptive-icon>
```

- [ ] **Step 3: Create ic_launcher_round.xml** (identical for adaptive icons — round shape is handled by the launcher)

```xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_monochrome" />
</adaptive-icon>
```

---

### Task D4: Update AndroidManifest.xml with icon references

**Files:** Modify `android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1: Add icon attributes to `<application>` tag**

In `android/app/src/main/AndroidManifest.xml`, update the `<application>` opening tag to add `android:icon` and `android:roundIcon`:

```xml
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">
```

---

### Task D5: Compile check + feature doc + commit

- [ ] **Step 1: Compile**
```bash
cd android && ./gradlew :app:compileDebugKotlin
```
Expected: `BUILD SUCCESSFUL`

- [ ] **Step 2: Create feature doc** at `docs/features/app-icon.md`

```markdown
# Feature: App Icon
**Phase:** UI Overhaul | **Status:** complete

## What It Does
Custom adaptive launcher icon: white medical cross with a RED→YELLOW→GREEN arc below it, on a deep navy (#0A1628) background. Monochrome variant (cross only) for Android 13+ themed icons.

## Key Files
- `android/app/src/main/res/drawable/ic_launcher_foreground.xml` — cross + triage arc vector
- `android/app/src/main/res/drawable/ic_launcher_background.xml` — navy background
- `android/app/src/main/res/drawable/ic_launcher_monochrome.xml` — single-tone cross
- `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml` — adaptive icon manifest

## How to Test
Build APK and install on device. Check home screen and app drawer for icon. On Android 13+ device, enable themed icons in settings.

## Known Limitations
No PNG mipmap fallbacks generated (not required — minSdk=26 guarantees adaptive icon support on all target devices).
```

- [ ] **Step 3: Commit**
```bash
cd android && git add -A && git commit -m "feat: add custom adaptive launcher icon with medical cross and triage arc"
```

---

## Final Gate (after all phases complete)

- [ ] Run full test suite:
```bash
cd android && ./gradlew :app:testDebugUnitTest
```
Expected: `BUILD SUCCESSFUL`, all tests pass.

- [ ] Build debug APK:
```bash
cd android && ./gradlew :app:assembleDebug
```
Expected: `BUILD SUCCESSFUL`

- [ ] Verify `AndroidManifest.xml` has no `android.permission.INTERNET` (Rule 5):
```bash
grep -n "INTERNET" android/app/src/main/AndroidManifest.xml
```
Expected: no output.
