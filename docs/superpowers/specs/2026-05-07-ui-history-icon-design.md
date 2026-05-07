# Design: UI Overhaul, Patient History Screen, and App Icon
**Date:** 2026-05-07
**Status:** Approved

## Summary

Three coordinated improvements to the Gemma Triage Android app:
1. **UI overhaul** — Material Design 3 upgrade with animations (mic pulse, color transitions, stage indicators)
2. **Patient history screen** — Swipe-left ViewPager2 page showing all past patients with expandable detail cards
3. **App icon** — Custom adaptive launcher icon (medical cross + triage arc)

No new library dependencies beyond what Material 3 (already a transitive AndroidX dep) and standard Android provide.

---

## 1. Navigation Architecture

### Structure
`MainActivity` becomes a thin shell containing a `ViewPager2` with two pages:

| Page | Fragment | Purpose |
|------|----------|---------|
| 0 | `TriageFragment` | All current triage workflow |
| 1 | `HistoryFragment` | Past patient records |

A 2-dot `TabLayout` indicator at the bottom shows current page. No top action bar — field app, every pixel counts.

### Data flow
`TriageViewModel` gains:
- `val history: StateFlow<List<TriageRecord>>` — loaded from Room on init, refreshed after every `outputManager.process()` call
- `HistoryFragment` observes this flow directly (no separate ViewModel)

### File changes
- `MainActivity.kt` — strip to ViewPager2 shell + TabLayout indicator
- `TriageFragment.kt` — new Fragment holding all current `MainActivity` triage logic
- `HistoryFragment.kt` — new Fragment with RecyclerView
- `TriagePagerAdapter.kt` — `FragmentStateAdapter` for the two pages
- `activity_main.xml` — replaced with ViewPager2 + TabLayout layout
- `fragment_triage.xml` — current `activity_main.xml` content (upgraded)
- `fragment_history.xml` — new history layout

---

## 2. Triage Screen (Material 3 Overhaul)

### Mic / action button
- `ExtendedFAB`, full-width, bottom of screen
- Label state machine:
  - Idle / model ready → `"Start Triage"`
  - Listening → `"Listening…"` + `AnimatedVectorDrawable` 3-ring pulse plays
  - Transcribing / Analyzing → `"Analyzing…"` + `CircularProgressIndicator` (indeterminate, centered above button)
  - Speaking → `"Speaking…"` (button disabled)
  - Follow-up listening → `"Ask a question…"`

### Status feedback
- `LinearProgressIndicator` (indeterminate, full-width) replaces `tvStatus` text during active states
- Status text (`tvStatus`) remains for error messages and idle label only

### Result card
- `MaterialCardView` with `app:strokeWidth="3dp"` and `app:strokeColor` set to triage code color
- On result arrival:
  1. Card background flashes from surface to 15%-tinted triage color via `ValueAnimator` (300ms), then fades back to surface (500ms)
  2. Triage code `TextView` animates in with `scaleX`/`scaleY` 0→1 via `OvershootInterpolator` (400ms)
- Triage code colors: RED `#D32F2F`, YELLOW `#F9A825`, GREEN `#388E3C`, BLACK `#212121`

### Conversation bubbles
- Replace raw `TextView` in `ScrollView` with `RecyclerView` of small `MaterialCardView` bubbles
- Q (user): left-aligned, dark tint
- A (model): right-aligned, accent tint
- Auto-scrolls to bottom on new entry

### Next Patient button
- `MaterialButton` outlined style
- Hidden off-screen below (translateY = +200dp) until `ResultReady`
- Animates up with `ObjectAnimator` on `translationY` (300ms, `DecelerateInterpolator`) when result arrives
- Animates back down on tap before resetting to Idle

---

## 3. History Screen

### List (collapsed state)
Each `MaterialCardView` row shows:
- Colored triage code `Chip` (badge — non-interactive)
- Formatted timestamp: `"May 7 · 14:32"`
- Confidence: `"97% confidence"`
- Transcription preview: single line, ellipsized at end

### Expand on tap
`TransitionManager.beginDelayedTransition(recyclerView)` triggers animated height change revealing:
- Full transcription text
- Immediate steps (numbered, from `smsPayload` or stored steps)
- SMS payload block (monospace font, `@color/on_surface_secondary`)
- Transmitted badge: green `"SMS sent"` chip or grey `"Pending"` chip based on `isTransmitted`

Only one card expanded at a time — tapping another collapses the current one.

### Header + empty state
- Sticky header: `"N patients triaged today"` (count of records with today's date)
- Empty state: centered icon + `"No patients triaged yet."` text when list is empty

### Adapter
- `HistoryAdapter : RecyclerView.Adapter<HistoryAdapter.ViewHolder>`
- Tracks `expandedPosition: Int = -1`
- `notifyItemChanged` on both old and new expanded positions

---

## 4. App Icon

### Adaptive icon (Android 8+)
- **Foreground** (`ic_launcher_foreground.xml`): White medical cross centered, with a 3-color arc (RED → YELLOW → GREEN) sweeping around the lower portion of the cross
- **Background** (`ic_launcher_background.xml`): Solid deep navy `#0A1628`
- **Monochrome** (`ic_launcher_monochrome.xml`): Cross silhouette only, single tone (for Android 13+ themed icons)

### Legacy fallbacks
Standard `mipmap-mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi` PNG exports from the vector at correct sizes (48/72/96/144/192 dp).

### Manifest
`AndroidManifest.xml` `<application>` tag updated:
```xml
android:icon="@mipmap/ic_launcher"
android:roundIcon="@mipmap/ic_launcher_round"
```

---

## 5. TriageRecord Data Model

`TriageRecord` needs one new field to display immediate steps in history detail:

```kotlin
@Entity(tableName = "triage_records")
data class TriageRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val timestamp: Long,
    val triageCode: String,
    val confidence: Double,
    val transcription: String,
    val immediateSteps: String,   // NEW — newline-joined list from TriageResult
    val smsPayload: String,
    val isTransmitted: Boolean = false
)
```

Room DB version bumps **1 → 2** with `fallbackToDestructiveMigration()` (acceptable for hackathon — no prod data to preserve).

`TriageOutputManager.process()` is updated to pass `result.immediateSteps.joinToString("\n")` into the new field.

`TriageViewModel` adds:
```kotlin
private val _history = MutableStateFlow<List<TriageRecord>>(emptyList())
val history: StateFlow<List<TriageRecord>> = _history
```
Refreshed via `viewModelScope.launch { _history.value = db.triageDao().getAllRecords() }` on init and after each `outputManager.process()` call.

---

## Out of Scope
- File export of history (not needed)
- Internet connectivity (never)
- New library dependencies beyond Material 3 (already present)
- Jetpack Compose (View system only)

---

## Implementation Phases

| Phase | Scope | Agent |
|-------|-------|-------|
| A | Navigation refactor (MainActivity → ViewPager2 + two Fragments) | subagent |
| B | Triage screen Material 3 upgrade + animations | subagent |
| C | History screen (HistoryFragment + HistoryAdapter + ViewModel history flow) | subagent |
| D | App icon (vector drawables + mipmap + manifest) | subagent |

Phases A and D are independent of B and C. A must complete before B and C start. B and C can run in parallel after A.
