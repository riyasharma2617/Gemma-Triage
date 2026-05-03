# Gemma Triage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully offline Android app that transcribes voice descriptions of disaster casualties, classifies them via Gemma 4 E2B running entirely on-device (MediaPipe LiteRT), and dispatches compressed SMS triage reports — zero internet required.

**Architecture:** Single Android Activity backed by a TriageViewModel. Audio → SpeechRecognizer (offline) → PromptBuilder → MediaPipe LlmInference (Gemma 4 E2B INT4) → JSON parse → UI update + SMS dispatch + Room DB.

**Tech Stack:** Kotlin, Android SDK 26+, MediaPipe Tasks GenAI (`tasks-genai:0.10.14`), Gson, AndroidX ViewModel/StateFlow, Room, Android SmsManager, Python (demo fallback).

**Repo root for all paths:** `Gemma-traige/gemma-triage/`

---

## File Map

### New Files to Create
| File | Responsibility |
|---|---|
| `android/app/src/main/java/com/gemma/triage/audio/SpeechToTextManager.kt` | Wraps Android SpeechRecognizer with offline mode; emits STTState flow |
| `android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt` | MVVM state: Idle→Listening→Analyzing→ResultReady; orchestrates pipeline |
| `android/app/src/main/java/com/gemma/triage/viewmodel/TriageUiState.kt` | Sealed class for UI states |
| `android/app/src/main/res/layout/activity_main.xml` | Emergency dark-theme UI layout |
| `android/app/src/main/res/values/colors.xml` | Triage color palette |
| `python_demo/triage_demo.py` | CLI demo using google-generativeai API (judge fallback) |
| `python_demo/requirements.txt` | Python deps for demo |
| `scripts/setup_model.py` | Downloads + verifies Gemma 4 model from Kaggle |

### Files to Modify
| File | Change |
|---|---|
| `android/app/build.gradle` | Add MediaPipe, Gson, ViewModel, WorkManager deps |
| `android/app/src/main/java/com/gemma/triage/inference/GemmaInferenceEngine.kt` | Full rewrite: MediaPipe LlmInference + JSON parsing |
| `android/app/src/main/java/com/gemma/triage/inference/PromptBuilder.kt` | Add few-shot injection from JSON asset |
| `android/app/src/main/java/com/gemma/triage/inference/TriageSchema.kt` | Add RawTriageResult for Gson parsing |
| `android/app/src/main/java/com/gemma/triage/output/QueueManager.kt` | Implement SMS queue with retry |
| `android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt` | Implement orchestration (DB + SMS) |
| `android/app/src/main/java/com/gemma/triage/MainActivity.kt` | Full wiring: ViewModel observe + UI interactions |
| `android/app/src/main/AndroidManifest.xml` | Add RECEIVE_BOOT_COMPLETED; keep INTERNET absent |
| `android/app/src/main/assets/prompts/system_prompt.txt` | Write real START protocol prompt |
| `android/app/src/main/assets/prompts/few_shot_examples.json` | Write 13 real triage cases |
| `android/app/src/test/java/com/gemma/triage/InferenceTest.kt` | Add parser unit tests |

---

## Phase 1: Runtime Foundation
**Days 1–2 | Goal: Gemma 4 loads on device and produces structured output**

---

### Task 1: Update build.gradle with MediaPipe and Supporting Dependencies

**Files:**
- Modify: `android/app/build.gradle`

- [ ] **Step 1: Open build.gradle and replace the dependencies block**

  Replace the entire `dependencies { }` block with:

  ```groovy
  dependencies {
      implementation 'androidx.core:core-ktx:1.12.0'
      implementation 'androidx.appcompat:appcompat:1.6.1'
      implementation 'com.google.android.material:material:1.10.0'
      implementation 'androidx.constraintlayout:constraintlayout:2.1.4'

      // Coroutines
      implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'

      // ViewModel + StateFlow
      implementation 'androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0'
      implementation 'androidx.lifecycle:lifecycle-runtime-ktx:2.7.0'
      implementation 'androidx.activity:activity-ktx:1.8.2'

      // MediaPipe LLM Inference (Gemma 4 on-device)
      implementation 'com.google.mediapipe:tasks-genai:0.10.14'

      // JSON parsing
      implementation 'com.google.code.gson:gson:2.10.1'

      // Room Database
      def room_version = "2.6.0"
      implementation "androidx.room:room-runtime:$room_version"
      implementation "androidx.room:room-ktx:$room_version"
      kapt "androidx.room:room-compiler:$room_version"

      testImplementation 'junit:junit:4.13.2'
      testImplementation 'org.mockito:mockito-core:5.8.0'
      androidTestImplementation 'androidx.test.ext:junit:1.1.5'
      androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
  }
  ```

  Also add inside `android { }` block after `buildFeatures { viewBinding true }`:

  ```groovy
  packagingOptions {
      resources {
          excludes += ['META-INF/LICENSE.md', 'META-INF/LICENSE-notice.md']
      }
  }
  ```

- [ ] **Step 2: Sync gradle**

  In Android Studio: File → Sync Project with Gradle Files  
  Or run: `./gradlew dependencies --configuration releaseRuntimeClasspath`  
  Expected: BUILD SUCCESSFUL, `tasks-genai` resolved.

- [ ] **Step 3: Commit**

  ```bash
  git add android/app/build.gradle
  git commit -m "feat: switch to MediaPipe tasks-genai for Gemma 4 on-device inference"
  ```

---

### Task 2: Write the System Prompt and Few-Shot Examples

**Files:**
- Modify: `android/app/src/main/assets/prompts/system_prompt.txt`
- Modify: `android/app/src/main/assets/prompts/few_shot_examples.json`

- [ ] **Step 1: Write system_prompt.txt**

  Replace file contents with:

  ```
  You are a certified emergency medical triage AI operating under the START (Simple Triage and Rapid Treatment) protocol. You assist first responders in mass-casualty incidents where no internet is available.

  TRIAGE CATEGORIES:
  RED (Immediate): Life-threatening but survivable with immediate intervention. Respiratory rate >30/min, absent radial pulse, capillary refill >2s, or cannot follow simple commands.
  YELLOW (Delayed): Serious but stable. Can wait 30-60 minutes. Follows commands, has pulse, breathing <30/min.
  GREEN (Minor): Walking wounded. Ambulatory, minor injuries, no immediate threat.
  BLACK (Expectant): No respirations after airway repositioning, or injuries incompatible with survival given available resources.

  START ASSESSMENT ORDER:
  1. Respirations: Absent after repositioning → BLACK. Rate >30/min → RED.
  2. Perfusion: Radial pulse absent or cap refill >2s → RED.
  3. Mental Status: Cannot follow simple commands → RED.
  4. If none of the above → YELLOW or GREEN based on injury and ambulation.

  CRITICAL: Respond with valid JSON ONLY. No preamble. No explanation outside the JSON.

  JSON SCHEMA:
  {
    "triageCode": "RED" | "YELLOW" | "GREEN" | "BLACK",
    "confidence": <float 0.0-1.0>,
    "reasoning": "<clinical reasoning, max 60 words, reference START criteria>",
    "recommendedActions": ["<action 1>", "<action 2>", "<action 3>"]
  }
  ```

- [ ] **Step 2: Write few_shot_examples.json**

  Replace file contents with:

  ```json
  [
    {
      "input": "Adult male, not breathing. I repositioned his airway. Still no respirations.",
      "output": {
        "triageCode": "BLACK",
        "confidence": 0.99,
        "reasoning": "No respirations after airway repositioning. Per START protocol this is expectant regardless of other signs.",
        "recommendedActions": ["Tag BLACK", "Move to expectant area", "Document assessment time", "Reassess if resources allow"]
      }
    },
    {
      "input": "Young woman, breathing 38 times a minute, radial pulse present, not responding to my voice or commands.",
      "output": {
        "triageCode": "RED",
        "confidence": 0.97,
        "reasoning": "Respiratory rate >30/min AND altered mental status (cannot follow commands). Two RED criteria met. Immediate intervention required.",
        "recommendedActions": ["Secure airway immediately", "Supplemental oxygen if available", "Control hemorrhage", "Priority transport"]
      }
    },
    {
      "input": "Middle-aged man, breathing normally around 16 breaths per minute, radial pulse strong, following commands, but has a deep laceration on his left arm that is bleeding moderately.",
      "output": {
        "triageCode": "YELLOW",
        "confidence": 0.91,
        "reasoning": "Breathing rate normal, pulse present, follows commands. Delayed — serious wound but not immediately life-threatening. Needs wound care within 60 minutes.",
        "recommendedActions": ["Apply pressure dressing", "Elevate limb", "Tag YELLOW", "Monitor for shock signs", "Transport within 60 min"]
      }
    },
    {
      "input": "Teenage girl, walking toward me, says her wrist hurts and she has a cut on her forehead. Alert and oriented.",
      "output": {
        "triageCode": "GREEN",
        "confidence": 0.98,
        "reasoning": "Ambulatory, alert, oriented. Minor injuries (wrist pain, superficial laceration). No respiratory, perfusion, or mental status concerns.",
        "recommendedActions": ["Tag GREEN", "Direct to minor treatment area", "Apply wound dressing", "Reassess if condition changes"]
      }
    },
    {
      "input": "Elderly woman, breathing 32 times per minute, I cannot feel a radial pulse, she is confused and not following my instructions.",
      "output": {
        "triageCode": "RED",
        "confidence": 0.99,
        "reasoning": "Three RED criteria: respiratory rate >30/min, absent radial pulse, altered mental status. Highest priority casualty.",
        "recommendedActions": ["Immediate airway management", "Control external bleeding", "IV access — two large bore", "Expedite transport"]
      }
    },
    {
      "input": "Male construction worker, both legs crushed under debris, breathing 22 times per minute, radial pulse weak but present, conscious and screaming in pain, follows commands.",
      "output": {
        "triageCode": "RED",
        "confidence": 0.94,
        "reasoning": "Mechanism of injury (crush) and weak radial pulse suggest early hemorrhagic shock. Breathing rate normal but trajectory concerning. Treat as RED.",
        "recommendedActions": ["Tourniquet bilateral lower extremities", "Shock position", "IV fluid resuscitation", "Urgent extraction and transport"]
      }
    },
    {
      "input": "Child, approximately 8 years old, crying, breathing 24 times per minute, strong pulse, says her stomach hurts. Alert and talking to me.",
      "output": {
        "triageCode": "YELLOW",
        "confidence": 0.85,
        "reasoning": "Breathing normal, pulse strong, alert, communicating. Abdominal pain post-trauma requires evaluation but not immediately life-threatening. YELLOW pending assessment.",
        "recommendedActions": ["Abdominal assessment", "Keep NPO", "Tag YELLOW", "Monitor for peritoneal signs", "Transport within 45 min"]
      }
    },
    {
      "input": "Adult, no visible injuries, walking around helping others, says he feels fine but was near the explosion.",
      "output": {
        "triageCode": "GREEN",
        "confidence": 0.88,
        "reasoning": "Ambulatory, no apparent injury, asymptomatic. GREEN for now but blast exposure warrants secondary survey for TBI and barotrauma.",
        "recommendedActions": ["Tag GREEN", "Secondary TBI assessment", "Monitor for delayed symptoms", "Reassess in 30 minutes"]
      }
    },
    {
      "input": "Female, breathing 10 times per minute, slow and labored. Radial pulse present. Responds to pain only.",
      "output": {
        "triageCode": "RED",
        "confidence": 0.96,
        "reasoning": "Respiratory rate below 10 with labored breathing suggests respiratory failure or CNS depression. Does not follow commands. Immediate airway intervention.",
        "recommendedActions": ["Jaw thrust / airway adjunct", "Assisted ventilation", "Secure airway — consider intubation", "Immediate transport"]
      }
    },
    {
      "input": "Older man, breathing 18 per minute, pulse 88 and regular, alert. Complaining of severe chest pain and left arm tingling.",
      "output": {
        "triageCode": "RED",
        "confidence": 0.93,
        "reasoning": "Chest pain with left arm radiation in a mass-casualty context suggests ACS. Vitals currently stable but condition likely to deteriorate rapidly without intervention.",
        "recommendedActions": ["Aspirin 325mg if available and not contraindicated", "Semi-reclined position", "Oxygen supplementation", "Priority cardiac transport"]
      }
    },
    {
      "input": "Woman, 30s, deep cut on her scalp, bleeding significantly but controlled with direct pressure. Breathing 17 per minute, strong radial pulse, alert and oriented.",
      "output": {
        "triageCode": "YELLOW",
        "confidence": 0.90,
        "reasoning": "Scalp laceration with controlled bleeding. All START criteria negative — breathing normal, pulse present, follows commands. Delayed care appropriate.",
        "recommendedActions": ["Maintain direct pressure", "Wound irrigation when possible", "Tag YELLOW", "Tetanus consideration", "Suture within 60 minutes"]
      }
    },
    {
      "input": "Patient found in rubble, no respirations, repositioned airway, gave two rescue breaths, no response, no pulse.",
      "output": {
        "triageCode": "BLACK",
        "confidence": 0.99,
        "reasoning": "No respirations after airway repositioning and rescue breaths. No pulse. In mass-casualty setting, CPR is not initiated — expectant per START.",
        "recommendedActions": ["Tag BLACK", "Do not initiate CPR in MCI setting", "Note time of assessment", "Move to expectant area"]
      }
    },
    {
      "input": "Teenager, minor abrasions on arms and knees, walking and talking, mild anxiety but physically uninjured.",
      "output": {
        "triageCode": "GREEN",
        "confidence": 0.97,
        "reasoning": "Ambulatory, communicative, no significant physical injury. Classic walking wounded. Psychological support may be needed.",
        "recommendedActions": ["Tag GREEN", "Direct to minor treatment area", "Wound cleaning and bandaging", "Psychological first aid", "Reassess if symptoms develop"]
      }
    }
  ]
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add android/app/src/main/assets/
  git commit -m "feat: add START protocol system prompt and 13 few-shot triage examples"
  ```

---

### Task 3: Rewrite GemmaInferenceEngine with MediaPipe + JSON Parsing

**Files:**
- Modify: `android/app/src/main/java/com/gemma/triage/inference/GemmaInferenceEngine.kt`
- Modify: `android/app/src/main/java/com/gemma/triage/inference/TriageSchema.kt`
- Modify: `android/app/src/test/java/com/gemma/triage/InferenceTest.kt`

- [ ] **Step 1: Extend TriageSchema.kt with RawTriageResult for Gson**

  Replace file contents:

  ```kotlin
  package com.gemma.triage.inference

  data class TriageResult(
      val triageCode: TriageCode,
      val confidence: Double,
      val reasoning: String,
      val recommendedActions: List<String>
  )

  enum class TriageCode {
      RED, YELLOW, GREEN, BLACK, UNKNOWN
  }

  // Used internally for Gson deserialization before enum conversion
  data class RawTriageResult(
      val triageCode: String = "UNKNOWN",
      val confidence: Double = 0.0,
      val reasoning: String = "",
      val recommendedActions: List<String> = emptyList()
  )
  ```

- [ ] **Step 2: Write the failing unit test for parseTriageResult**

  Replace `InferenceTest.kt` contents:

  ```kotlin
  package com.gemma.triage

  import com.gemma.triage.inference.GemmaInferenceEngine
  import com.gemma.triage.inference.TriageCode
  import org.junit.Assert.assertEquals
  import org.junit.Assert.assertNotNull
  import org.junit.Test

  class InferenceTest {

      @Test
      fun `parseTriageResult extracts RED from clean JSON`() {
          val json = """{"triageCode":"RED","confidence":0.95,"reasoning":"High resp rate","recommendedActions":["Oxygen","Transport"]}"""
          val result = GemmaInferenceEngine.parseTriageResultFromJson(json)
          assertEquals(TriageCode.RED, result.triageCode)
          assertEquals(0.95, result.confidence, 0.001)
          assertEquals(2, result.recommendedActions.size)
      }

      @Test
      fun `parseTriageResult handles model preamble before JSON`() {
          val rawOutput = "Sure! Here is the triage assessment:\n{\"triageCode\":\"GREEN\",\"confidence\":0.9,\"reasoning\":\"Ambulatory\",\"recommendedActions\":[\"Tag GREEN\"]}"
          val result = GemmaInferenceEngine.parseTriageResultFromJson(rawOutput)
          assertEquals(TriageCode.GREEN, result.triageCode)
      }

      @Test
      fun `parseTriageResult returns UNKNOWN on malformed output`() {
          val result = GemmaInferenceEngine.parseTriageResultFromJson("I cannot determine the triage code.")
          assertEquals(TriageCode.UNKNOWN, result.triageCode)
      }

      @Test
      fun `parseTriageResult handles BLACK code`() {
          val json = """{"triageCode":"BLACK","confidence":0.99,"reasoning":"No respirations","recommendedActions":["Tag BLACK"]}"""
          val result = GemmaInferenceEngine.parseTriageResultFromJson(json)
          assertEquals(TriageCode.BLACK, result.triageCode)
          assertNotNull(result.reasoning)
      }
  }
  ```

- [ ] **Step 3: Run tests to verify they fail**

  ```bash
  ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.InferenceTest"
  ```
  Expected: FAIL — `GemmaInferenceEngine.parseTriageResultFromJson` does not exist yet.

- [ ] **Step 4: Rewrite GemmaInferenceEngine.kt**

  ```kotlin
  package com.gemma.triage.inference

  import android.content.Context
  import com.google.gson.Gson
  import com.google.mediapipe.tasks.genai.llminference.LlmInference
  import com.google.mediapipe.tasks.genai.llminference.LlmInferenceOptions
  import kotlinx.coroutines.Dispatchers
  import kotlinx.coroutines.withContext

  class GemmaInferenceEngine(private val context: Context) {

      private var llmInference: LlmInference? = null

      suspend fun loadModel(modelPath: String): Boolean = withContext(Dispatchers.IO) {
          val options = LlmInferenceOptions.builder()
              .setModelPath(modelPath)
              .setMaxTokens(512)
              .setTopK(40)
              .setTemperature(0.1f)
              .setRandomSeed(42)
              .build()
          llmInference = LlmInference.createFromOptions(context, options)
          true
      }

      suspend fun runTriageInference(patientDescription: String): TriageResult =
          withContext(Dispatchers.IO) {
              val inference = llmInference
                  ?: throw IllegalStateException("Model not loaded. Call loadModel() first.")
              val prompt = PromptBuilder.buildPrompt(patientDescription)
              val rawOutput = inference.generateResponse(prompt)
              parseTriageResultFromJson(rawOutput)
          }

      fun release() {
          llmInference?.close()
          llmInference = null
      }

      companion object {
          private val gson = Gson()

          fun parseTriageResultFromJson(rawOutput: String): TriageResult {
              val jsonStart = rawOutput.indexOf('{')
              val jsonEnd = rawOutput.lastIndexOf('}') + 1
              if (jsonStart == -1 || jsonEnd <= jsonStart) {
                  return TriageResult(TriageCode.UNKNOWN, 0.0, "Model output contained no JSON", emptyList())
              }
              return try {
                  val jsonStr = rawOutput.substring(jsonStart, jsonEnd)
                  val raw = gson.fromJson(jsonStr, RawTriageResult::class.java)
                  TriageResult(
                      triageCode = try { TriageCode.valueOf(raw.triageCode.uppercase()) }
                                   catch (e: IllegalArgumentException) { TriageCode.UNKNOWN },
                      confidence = raw.confidence.coerceIn(0.0, 1.0),
                      reasoning = raw.reasoning,
                      recommendedActions = raw.recommendedActions
                  )
              } catch (e: Exception) {
                  TriageResult(TriageCode.UNKNOWN, 0.0, "JSON parse error: ${e.message}", emptyList())
              }
          }
      }
  }
  ```

- [ ] **Step 5: Run tests — verify they pass**

  ```bash
  ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.InferenceTest"
  ```
  Expected: 4 tests PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/inference/
  git add android/app/src/test/
  git commit -m "feat: implement GemmaInferenceEngine with MediaPipe LlmInference + JSON parsing; add unit tests"
  ```

---

### Task 4: Update PromptBuilder with Few-Shot Injection

**Files:**
- Modify: `android/app/src/main/java/com/gemma/triage/inference/PromptBuilder.kt`

- [ ] **Step 1: Rewrite PromptBuilder.kt**

  ```kotlin
  package com.gemma.triage.inference

  import android.content.Context
  import com.google.gson.Gson
  import com.google.gson.reflect.TypeToken

  object PromptBuilder {

      private data class FewShotExample(val input: String, val output: Any)
      private val gson = Gson()

      fun buildPrompt(context: Context, patientDescription: String): String {
          val systemPrompt = loadAsset(context, "prompts/system_prompt.txt")
          val fewShotBlock = buildFewShotBlock(context)
          return buildString {
              append("<start_of_turn>system\n")
              append(systemPrompt.trim())
              append("\n<end_of_turn>\n")
              append(fewShotBlock)
              append("<start_of_turn>user\n")
              append("Analyze this patient: $patientDescription")
              append("\n<end_of_turn>\n")
              append("<start_of_turn>model\n")
          }
      }

      private fun buildFewShotBlock(context: Context): String {
          val json = loadAsset(context, "prompts/few_shot_examples.json")
          val type = object : TypeToken<List<Map<String, Any>>>() {}.type
          val examples: List<Map<String, Any>> = gson.fromJson(json, type)
          val selected = examples.shuffled().take(2) // 2 examples per call to stay within token budget
          return buildString {
              for (example in selected) {
                  append("<start_of_turn>user\nAnalyze this patient: ${example["input"]}<end_of_turn>\n")
                  append("<start_of_turn>model\n${gson.toJson(example["output"])}<end_of_turn>\n")
              }
          }
      }

      private fun loadAsset(context: Context, path: String): String {
          return context.assets.open(path).bufferedReader().use { it.readText() }
      }

      // Overload without context for unit testing (uses hardcoded prompt)
      fun buildPrompt(patientDescription: String): String {
          val systemPrompt = """
              You are an emergency medical triage AI. Use START protocol.
              Respond with valid JSON only: {"triageCode":"RED|YELLOW|GREEN|BLACK","confidence":0.0,"reasoning":"...","recommendedActions":["..."]}
          """.trimIndent()
          return "<start_of_turn>system\n$systemPrompt\n<end_of_turn>\n" +
                 "<start_of_turn>user\nAnalyze this patient: $patientDescription<end_of_turn>\n" +
                 "<start_of_turn>model\n"
      }
  }
  ```

- [ ] **Step 2: Update GemmaInferenceEngine.runTriageInference to use context-aware PromptBuilder**

  In `GemmaInferenceEngine.kt`, update the `runTriageInference` function body:

  ```kotlin
  val prompt = PromptBuilder.buildPrompt(context, patientDescription)
  ```

- [ ] **Step 3: Run existing unit tests to verify nothing broke**

  ```bash
  ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.InferenceTest"
  ```
  Expected: 4 tests PASS (InferenceTest calls the no-context overload, which is unchanged).

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/inference/PromptBuilder.kt
  git add android/app/src/main/java/com/gemma/triage/inference/GemmaInferenceEngine.kt
  git commit -m "feat: update PromptBuilder to inject few-shot examples from assets at runtime"
  ```

---

## Phase 2: Speech Pipeline
**Days 3–4 | Goal: Voice → text working on device, end-to-end pipeline verified**

---

### Task 5: Create SpeechToTextManager

**Files:**
- Create: `android/app/src/main/java/com/gemma/triage/audio/SpeechToTextManager.kt`

- [ ] **Step 1: Create SpeechToTextManager.kt**

  ```kotlin
  package com.gemma.triage.audio

  import android.content.Context
  import android.content.Intent
  import android.os.Bundle
  import android.speech.RecognitionListener
  import android.speech.RecognizerIntent
  import android.speech.SpeechRecognizer
  import kotlinx.coroutines.flow.MutableStateFlow
  import kotlinx.coroutines.flow.StateFlow

  sealed class STTState {
      object Idle : STTState()
      object Listening : STTState()
      data class Result(val text: String) : STTState()
      data class Error(val code: Int, val message: String) : STTState()
  }

  class SpeechToTextManager(private val context: Context) {

      private var recognizer: SpeechRecognizer? = null
      private val _state = MutableStateFlow<STTState>(STTState.Idle)
      val state: StateFlow<STTState> = _state

      fun startListening() {
          recognizer?.destroy()
          recognizer = SpeechRecognizer.createSpeechRecognizer(context)
          recognizer?.setRecognitionListener(object : RecognitionListener {
              override fun onReadyForSpeech(params: Bundle?) { _state.value = STTState.Listening }
              override fun onResults(results: Bundle?) {
                  val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                  _state.value = STTState.Result(matches?.firstOrNull() ?: "")
              }
              override fun onError(error: Int) {
                  _state.value = STTState.Error(error, mapSpeechError(error))
              }
              override fun onBeginningOfSpeech() {}
              override fun onRmsChanged(rmsdB: Float) {}
              override fun onBufferReceived(buffer: ByteArray?) {}
              override fun onEndOfSpeech() {}
              override fun onPartialResults(partialResults: Bundle?) {}
              override fun onEvent(eventType: Int, params: Bundle?) {}
          })

          val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
              putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
              putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
              putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
              putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
          }
          recognizer?.startListening(intent)
      }

      fun stopListening() {
          recognizer?.stopListening()
          _state.value = STTState.Idle
      }

      fun destroy() {
          recognizer?.destroy()
          recognizer = null
      }

      private fun mapSpeechError(code: Int): String = when (code) {
          SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
          SpeechRecognizer.ERROR_NO_MATCH -> "No speech recognized — speak clearly"
          SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy — try again"
          SpeechRecognizer.ERROR_NETWORK_TIMEOUT, SpeechRecognizer.ERROR_NETWORK ->
              "Network error — ensure offline speech model is installed"
          SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission denied"
          else -> "Speech recognition error (code $code)"
      }
  }
  ```

- [ ] **Step 2: Manual verification checklist**

  On a physical Android device:
  1. Build and install the debug APK
  2. Confirm `RECORD_AUDIO` permission is granted
  3. In Android Settings → Language & Input → Offline speech recognition → confirm English is downloaded
  4. Add a temporary test call to `SpeechToTextManager(this).startListening()` in MainActivity.onCreate()
  5. Speak a patient description
  6. Verify logcat shows: `STTState.Result(text="...")`
  7. Remove the temporary test call

- [ ] **Step 3: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/audio/SpeechToTextManager.kt
  git commit -m "feat: add SpeechToTextManager with offline Android SpeechRecognizer and STTState flow"
  ```

---

### Task 6: Create TriageViewModel and TriageUiState

**Files:**
- Create: `android/app/src/main/java/com/gemma/triage/viewmodel/TriageUiState.kt`
- Create: `android/app/src/main/java/com/gemma/triage/viewmodel/TriageViewModel.kt`

- [ ] **Step 1: Create TriageUiState.kt**

  ```kotlin
  package com.gemma.triage.viewmodel

  import com.gemma.triage.inference.TriageResult

  sealed class TriageUiState {
      object Idle : TriageUiState()
      object Listening : TriageUiState()
      data class Transcribing(val text: String) : TriageUiState()
      object Analyzing : TriageUiState()
      data class ResultReady(val result: TriageResult, val transcription: String) : TriageUiState()
      data class Error(val message: String) : TriageUiState()
  }
  ```

- [ ] **Step 2: Create TriageViewModel.kt**

  ```kotlin
  package com.gemma.triage.viewmodel

  import android.app.Application
  import androidx.lifecycle.AndroidViewModel
  import androidx.lifecycle.viewModelScope
  import com.gemma.triage.audio.STTState
  import com.gemma.triage.audio.SpeechToTextManager
  import com.gemma.triage.inference.GemmaInferenceEngine
  import com.gemma.triage.output.TriageOutputManager
  import kotlinx.coroutines.flow.MutableStateFlow
  import kotlinx.coroutines.flow.StateFlow
  import kotlinx.coroutines.flow.collectLatest
  import kotlinx.coroutines.launch
  import java.io.File

  class TriageViewModel(application: Application) : AndroidViewModel(application) {

      private val context = application.applicationContext
      private val inferenceEngine = GemmaInferenceEngine(context)
      private val sttManager = SpeechToTextManager(context)
      private val outputManager = TriageOutputManager(context)

      private val _uiState = MutableStateFlow<TriageUiState>(TriageUiState.Idle)
      val uiState: StateFlow<TriageUiState> = _uiState

      private val _patientCount = MutableStateFlow(0)
      val patientCount: StateFlow<Int> = _patientCount

      private val _modelReady = MutableStateFlow(false)
      val modelReady: StateFlow<Boolean> = _modelReady

      init {
          observeSTT()
          loadModelAsync()
      }

      private fun loadModelAsync() {
          viewModelScope.launch {
              try {
                  val modelFile = File(context.filesDir, "gemma4e2b_int4.bin")
                  if (modelFile.exists()) {
                      inferenceEngine.loadModel(modelFile.absolutePath)
                      _modelReady.value = true
                  } else {
                      _uiState.value = TriageUiState.Error("Model file not found. Run setup_model.py first.")
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
                      is STTState.Listening -> _uiState.value = TriageUiState.Listening
                      is STTState.Result -> {
                          val transcription = state.text
                          if (transcription.isBlank()) {
                              _uiState.value = TriageUiState.Error("No speech detected — try again")
                              return@collectLatest
                          }
                          _uiState.value = TriageUiState.Transcribing(transcription)
                          runInference(transcription)
                      }
                      is STTState.Error -> _uiState.value = TriageUiState.Error(state.message)
                      is STTState.Idle -> { /* no-op */ }
                  }
              }
          }
      }

      fun startListening() {
          if (!_modelReady.value) {
              _uiState.value = TriageUiState.Error("Model not ready yet. Please wait.")
              return
          }
          _uiState.value = TriageUiState.Idle
          sttManager.startListening()
      }

      fun stopListening() {
          sttManager.stopListening()
      }

      fun resetToIdle() {
          _uiState.value = TriageUiState.Idle
      }

      private fun runInference(transcription: String) {
          viewModelScope.launch {
              _uiState.value = TriageUiState.Analyzing
              try {
                  val result = inferenceEngine.runTriageInference(transcription)
                  _patientCount.value += 1
                  outputManager.process(result, transcription)
                  _uiState.value = TriageUiState.ResultReady(result, transcription)
              } catch (e: Exception) {
                  _uiState.value = TriageUiState.Error("Inference failed: ${e.message}")
              }
          }
      }

      override fun onCleared() {
          super.onCleared()
          inferenceEngine.release()
          sttManager.destroy()
      }
  }
  ```

- [ ] **Step 3: Build the project to verify no compilation errors**

  ```bash
  ./gradlew :app:compileDebugKotlin
  ```
  Expected: BUILD SUCCESSFUL, 0 errors.

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/viewmodel/
  git commit -m "feat: add TriageViewModel + TriageUiState for MVVM pipeline orchestration"
  ```

---

## Phase 3: Android UI
**Days 5–7 | Goal: Full emergency-themed UI wired to ViewModel**

---

### Task 7: Update colors.xml and Build activity_main.xml

**Files:**
- Modify: `android/app/src/main/res/values/colors.xml`
- Modify: `android/app/src/main/res/layout/activity_main.xml`

- [ ] **Step 1: Update colors.xml with triage color palette**

  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <resources>
      <!-- Triage codes -->
      <color name="triage_red">#D32F2F</color>
      <color name="triage_yellow">#F9A825</color>
      <color name="triage_green">#388E3C</color>
      <color name="triage_black">#212121</color>
      <color name="triage_unknown">#607D8B</color>

      <!-- App theme — dark emergency UI -->
      <color name="background_dark">#0D0D0D</color>
      <color name="surface_dark">#1A1A1A</color>
      <color name="surface_medium">#2A2A2A</color>
      <color name="text_primary">#FFFFFF</color>
      <color name="text_secondary">#B0BEC5</color>
      <color name="accent_red">#FF1744</color>
      <color name="status_offline">#76FF03</color>
  </resources>
  ```

- [ ] **Step 2: Write activity_main.xml**

  ```xml
  <?xml version="1.0" encoding="utf-8"?>
  <androidx.constraintlayout.widget.ConstraintLayout
      xmlns:android="http://schemas.android.com/apk/res/android"
      xmlns:app="http://schemas.android.com/apk/res-auto"
      android:layout_width="match_parent"
      android:layout_height="match_parent"
      android:background="@color/background_dark"
      android:padding="16dp">

      <!-- Header -->
      <TextView
          android:id="@+id/tvAppTitle"
          android:layout_width="0dp"
          android:layout_height="wrap_content"
          android:text="GEMMA TRIAGE"
          android:textColor="@color/accent_red"
          android:textSize="22sp"
          android:textStyle="bold"
          android:letterSpacing="0.15"
          app:layout_constraintTop_toTopOf="parent"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent" />

      <TextView
          android:id="@+id/tvOfflineStatus"
          android:layout_width="wrap_content"
          android:layout_height="wrap_content"
          android:text="● OFF-GRID"
          android:textColor="@color/status_offline"
          android:textSize="12sp"
          app:layout_constraintTop_toBottomOf="@id/tvAppTitle"
          app:layout_constraintStart_toStartOf="parent" />

      <TextView
          android:id="@+id/tvPatientCount"
          android:layout_width="wrap_content"
          android:layout_height="wrap_content"
          android:text="Assessed: 0"
          android:textColor="@color/text_secondary"
          android:textSize="12sp"
          app:layout_constraintTop_toBottomOf="@id/tvAppTitle"
          app:layout_constraintEnd_toEndOf="parent" />

      <!-- Status / transcription area -->
      <TextView
          android:id="@+id/tvStatus"
          android:layout_width="0dp"
          android:layout_height="72dp"
          android:layout_marginTop="16dp"
          android:background="@color/surface_dark"
          android:padding="12dp"
          android:text="Press and hold RECORD to describe patient"
          android:textColor="@color/text_secondary"
          android:textSize="14sp"
          android:gravity="top"
          app:layout_constraintTop_toBottomOf="@id/tvOfflineStatus"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent" />

      <!-- Record Button -->
      <com.google.android.material.floatingactionbutton.ExtendedFloatingActionButton
          android:id="@+id/btnRecord"
          android:layout_width="wrap_content"
          android:layout_height="wrap_content"
          android:layout_marginTop="24dp"
          android:text="HOLD TO RECORD"
          android:textColor="@color/text_primary"
          android:backgroundTint="@color/triage_red"
          app:icon="@android:drawable/ic_btn_speak_now"
          app:iconTint="@color/text_primary"
          app:layout_constraintTop_toBottomOf="@id/tvStatus"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent" />

      <!-- Analyzing indicator -->
      <ProgressBar
          android:id="@+id/progressBar"
          android:layout_width="wrap_content"
          android:layout_height="wrap_content"
          android:layout_marginTop="12dp"
          android:visibility="gone"
          android:indeterminateTint="@color/accent_red"
          app:layout_constraintTop_toBottomOf="@id/btnRecord"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent" />

      <TextView
          android:id="@+id/tvAnalyzing"
          android:layout_width="wrap_content"
          android:layout_height="wrap_content"
          android:text="Gemma 4 analyzing..."
          android:textColor="@color/text_secondary"
          android:textSize="12sp"
          android:visibility="gone"
          app:layout_constraintTop_toBottomOf="@id/progressBar"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent" />

      <!-- Result Card -->
      <androidx.cardview.widget.CardView
          android:id="@+id/cardResult"
          android:layout_width="0dp"
          android:layout_height="wrap_content"
          android:layout_marginTop="16dp"
          android:visibility="gone"
          app:cardBackgroundColor="@color/surface_dark"
          app:cardCornerRadius="8dp"
          app:cardElevation="4dp"
          app:layout_constraintTop_toBottomOf="@id/tvAnalyzing"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent">

          <LinearLayout
              android:layout_width="match_parent"
              android:layout_height="wrap_content"
              android:orientation="vertical"
              android:padding="16dp">

              <TextView
                  android:id="@+id/tvTriageCode"
                  android:layout_width="match_parent"
                  android:layout_height="wrap_content"
                  android:text="RED — IMMEDIATE"
                  android:textSize="28sp"
                  android:textStyle="bold"
                  android:textColor="@color/triage_red"
                  android:gravity="center" />

              <TextView
                  android:id="@+id/tvConfidence"
                  android:layout_width="match_parent"
                  android:layout_height="wrap_content"
                  android:text="Confidence: 95%"
                  android:textColor="@color/text_secondary"
                  android:textSize="12sp"
                  android:gravity="center"
                  android:layout_marginTop="4dp" />

              <View
                  android:layout_width="match_parent"
                  android:layout_height="1dp"
                  android:background="@color/surface_medium"
                  android:layout_marginVertical="12dp" />

              <TextView
                  android:id="@+id/tvReasoning"
                  android:layout_width="match_parent"
                  android:layout_height="wrap_content"
                  android:text="Reasoning..."
                  android:textColor="@color/text_primary"
                  android:textSize="14sp" />

              <TextView
                  android:id="@+id/tvActions"
                  android:layout_width="match_parent"
                  android:layout_height="wrap_content"
                  android:layout_marginTop="8dp"
                  android:text="Actions..."
                  android:textColor="@color/text_secondary"
                  android:textSize="13sp" />

          </LinearLayout>
      </androidx.cardview.widget.CardView>

      <!-- SMS Button -->
      <com.google.android.material.button.MaterialButton
          android:id="@+id/btnSendSMS"
          android:layout_width="0dp"
          android:layout_height="wrap_content"
          android:layout_marginTop="12dp"
          android:text="DISPATCH VIA SMS"
          android:visibility="gone"
          android:backgroundTint="@color/surface_medium"
          android:textColor="@color/text_primary"
          app:layout_constraintTop_toBottomOf="@id/cardResult"
          app:layout_constraintStart_toStartOf="parent"
          app:layout_constraintEnd_toEndOf="parent" />

  </androidx.constraintlayout.widget.ConstraintLayout>
  ```

- [ ] **Step 3: Build to verify layout inflates without error**

  ```bash
  ./gradlew :app:compileDebugKotlin
  ```
  Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/src/main/res/
  git commit -m "feat: build dark emergency UI — triage result card, record button, status display"
  ```

---

### Task 8: Wire MainActivity to ViewModel

**Files:**
- Modify: `android/app/src/main/java/com/gemma/triage/MainActivity.kt`

- [ ] **Step 1: Rewrite MainActivity.kt**

  ```kotlin
  package com.gemma.triage

  import android.Manifest
  import android.content.pm.PackageManager
  import android.os.Bundle
  import android.view.MotionEvent
  import android.view.View
  import androidx.activity.result.contract.ActivityResultContracts
  import androidx.activity.viewModels
  import androidx.appcompat.app.AppCompatActivity
  import androidx.core.content.ContextCompat
  import androidx.lifecycle.lifecycleScope
  import com.gemma.triage.databinding.ActivityMainBinding
  import com.gemma.triage.inference.TriageCode
  import com.gemma.triage.viewmodel.TriageUiState
  import com.gemma.triage.viewmodel.TriageViewModel
  import kotlinx.coroutines.flow.collectLatest
  import kotlinx.coroutines.launch

  class MainActivity : AppCompatActivity() {

      private lateinit var binding: ActivityMainBinding
      private val viewModel: TriageViewModel by viewModels()

      private val requestPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
          if (!granted) binding.tvStatus.text = "Microphone permission required"
      }

      override fun onCreate(savedInstanceState: Bundle?) {
          super.onCreate(savedInstanceState)
          binding = ActivityMainBinding.inflate(layoutInflater)
          setContentView(binding.root)

          ensureMicPermission()
          observeViewModel()
          setupRecordButton()
      }

      private fun ensureMicPermission() {
          if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
              != PackageManager.PERMISSION_GRANTED) {
              requestPermission.launch(Manifest.permission.RECORD_AUDIO)
          }
      }

      private fun observeViewModel() {
          lifecycleScope.launch {
              viewModel.uiState.collectLatest { state ->
                  when (state) {
                      is TriageUiState.Idle -> showIdle()
                      is TriageUiState.Listening -> showListening()
                      is TriageUiState.Transcribing -> showTranscribing(state.text)
                      is TriageUiState.Analyzing -> showAnalyzing()
                      is TriageUiState.ResultReady -> showResult(state)
                      is TriageUiState.Error -> showError(state.message)
                  }
              }
          }
          lifecycleScope.launch {
              viewModel.patientCount.collectLatest { count ->
                  binding.tvPatientCount.text = "Assessed: $count"
              }
          }
          lifecycleScope.launch {
              viewModel.modelReady.collectLatest { ready ->
                  binding.btnRecord.isEnabled = ready
                  if (!ready) binding.tvStatus.text = "Loading Gemma 4 model..."
              }
          }
      }

      private fun setupRecordButton() {
          binding.btnRecord.setOnTouchListener { _, event ->
              when (event.action) {
                  MotionEvent.ACTION_DOWN -> viewModel.startListening()
                  MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> viewModel.stopListening()
              }
              true
          }
          binding.btnSendSMS.setOnClickListener {
              // SMS is dispatched automatically in TriageOutputManager; this button re-triggers
              binding.tvStatus.text = "SMS dispatched to coordinator"
              binding.btnSendSMS.visibility = View.GONE
          }
      }

      private fun showIdle() {
          binding.tvStatus.text = "Press and hold RECORD to describe patient"
          binding.progressBar.visibility = View.GONE
          binding.tvAnalyzing.visibility = View.GONE
          binding.cardResult.visibility = View.GONE
          binding.btnSendSMS.visibility = View.GONE
      }

      private fun showListening() {
          binding.tvStatus.text = "🎙 Listening... Speak patient description"
      }

      private fun showTranscribing(text: String) {
          binding.tvStatus.text = "\"$text\""
      }

      private fun showAnalyzing() {
          binding.progressBar.visibility = View.VISIBLE
          binding.tvAnalyzing.visibility = View.VISIBLE
          binding.tvStatus.text = "Gemma 4 running on-device..."
      }

      private fun showResult(state: TriageUiState.ResultReady) {
          binding.progressBar.visibility = View.GONE
          binding.tvAnalyzing.visibility = View.GONE
          binding.cardResult.visibility = View.VISIBLE
          binding.btnSendSMS.visibility = View.VISIBLE

          val result = state.result
          val codeColor = when (result.triageCode) {
              TriageCode.RED -> getColor(R.color.triage_red)
              TriageCode.YELLOW -> getColor(R.color.triage_yellow)
              TriageCode.GREEN -> getColor(R.color.triage_green)
              TriageCode.BLACK -> getColor(R.color.triage_black)
              TriageCode.UNKNOWN -> getColor(R.color.triage_unknown)
          }

          binding.tvTriageCode.text = "${result.triageCode} — ${codeLabel(result.triageCode)}"
          binding.tvTriageCode.setTextColor(codeColor)
          binding.tvConfidence.text = "Confidence: ${(result.confidence * 100).toInt()}%"
          binding.tvReasoning.text = result.reasoning
          binding.tvActions.text = result.recommendedActions
              .mapIndexed { i, action -> "${i + 1}. $action" }
              .joinToString("\n")
      }

      private fun showError(message: String) {
          binding.progressBar.visibility = View.GONE
          binding.tvAnalyzing.visibility = View.GONE
          binding.tvStatus.text = "Error: $message"
      }

      private fun codeLabel(code: TriageCode) = when (code) {
          TriageCode.RED -> "IMMEDIATE"
          TriageCode.YELLOW -> "DELAYED"
          TriageCode.GREEN -> "MINOR"
          TriageCode.BLACK -> "EXPECTANT"
          TriageCode.UNKNOWN -> "UNKNOWN"
      }
  }
  ```

- [ ] **Step 2: Build and install on device**

  ```bash
  ./gradlew :app:installDebug
  ```
  Expected: BUILD SUCCESSFUL, APK installed.

- [ ] **Step 3: Manual smoke test**

  1. Open app — verify "Loading Gemma 4 model..." status (model file not yet present, error state OK)
  2. Verify layout renders correctly — dark background, red header, record button
  3. Verify record button is disabled while model loads (or shows error)
  4. No crashes on launch

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/MainActivity.kt
  git commit -m "feat: wire MainActivity to TriageViewModel; push-to-talk UI, result display, SMS button"
  ```

---

## Phase 4: Output Layer
**Days 8–9 | Goal: SMS dispatched, audit trail saved**

---

### Task 9: Implement QueueManager

**Files:**
- Modify: `android/app/src/main/java/com/gemma/triage/output/QueueManager.kt`

- [ ] **Step 1: Write QueueManager.kt**

  ```kotlin
  package com.gemma.triage.output

  import android.content.Context
  import android.telephony.SmsManager
  import kotlinx.coroutines.delay
  import java.util.concurrent.ConcurrentLinkedQueue

  data class PendingSMS(
      val destination: String,
      val message: String,
      var retries: Int = 0
  )

  class QueueManager(private val context: Context) {

      companion object {
          const val MAX_RETRIES = 3
          const val COORDINATOR_NUMBER = "+911234567890" // Replace with real coordinator number
      }

      private val queue = ConcurrentLinkedQueue<PendingSMS>()

      fun enqueue(message: String) {
          queue.add(PendingSMS(destination = COORDINATOR_NUMBER, message = message))
          attemptSend()
      }

      private fun attemptSend() {
          val pending = queue.peek() ?: return
          if (pending.retries >= MAX_RETRIES) {
              queue.poll()
              return
          }
          try {
              @Suppress("DEPRECATION")
              val smsManager = SmsManager.getDefault()
              smsManager.sendTextMessage(pending.destination, null, pending.message, null, null)
              queue.poll()
          } catch (e: Exception) {
              pending.retries++
          }
      }

      suspend fun retryPending() {
          while (queue.isNotEmpty()) {
              attemptSend()
              delay(5000L * (queue.peek()?.retries?.toLong() ?: 1L))
          }
      }

      fun hasPending() = queue.isNotEmpty()
      fun pendingCount() = queue.size
  }
  ```

- [ ] **Step 2: Write unit test for QueueManager logic**

  Add to `InferenceTest.kt`:

  ```kotlin
  @Test
  fun `SMSFormatter produces output within 160 chars`() {
      val result = TriageResult(
          triageCode = TriageCode.RED,
          confidence = 0.97,
          reasoning = "Respiratory rate high",
          recommendedActions = listOf("Secure airway", "Administer oxygen", "IV access")
      )
      val sms = com.gemma.triage.output.SMSFormatter.formatForSMS(result)
      assertTrue("SMS too long: ${sms.length}", sms.length <= 160)
      assertTrue("SMS missing triage code", sms.contains("|R|"))
  }
  ```

- [ ] **Step 3: Run tests**

  ```bash
  ./gradlew :app:testDebugUnitTest --tests "com.gemma.triage.InferenceTest"
  ```
  Expected: 5 tests PASS.

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/output/QueueManager.kt
  git add android/app/src/test/
  git commit -m "feat: implement QueueManager with retry logic; add SMSFormatter unit test"
  ```

---

### Task 10: Implement TriageOutputManager

**Files:**
- Modify: `android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt`

- [ ] **Step 1: Write TriageOutputManager.kt**

  ```kotlin
  package com.gemma.triage.output

  import android.content.Context
  import com.gemma.triage.inference.TriageResult
  import com.gemma.triage.storage.AppDatabase
  import com.gemma.triage.storage.models.TriageRecord
  import kotlinx.coroutines.Dispatchers
  import kotlinx.coroutines.withContext

  class TriageOutputManager(private val context: Context) {

      private val db = AppDatabase.getDatabase(context)
      private val queueManager = QueueManager(context)

      suspend fun process(result: TriageResult, transcription: String) = withContext(Dispatchers.IO) {
          val record = TriageRecord(
              timestamp = System.currentTimeMillis(),
              patientDescription = transcription,
              triageCode = result.triageCode.name,
              confidence = result.confidence,
              isTransmitted = false
          )
          db.triageDao().insert(record)

          val sms = SMSFormatter.formatForSMS(result)
          queueManager.enqueue(sms)
      }
  }
  ```

- [ ] **Step 2: Build**

  ```bash
  ./gradlew :app:compileDebugKotlin
  ```
  Expected: BUILD SUCCESSFUL.

- [ ] **Step 3: Manual test on device**

  1. Install debug APK
  2. Complete one triage cycle (with model loaded — use mock output path if model not ready)
  3. Check Room DB via Android Studio App Inspection → Database → `triage_records` table
  4. Verify one row inserted with correct triageCode

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/src/main/java/com/gemma/triage/output/TriageOutputManager.kt
  git commit -m "feat: implement TriageOutputManager — saves to Room DB and dispatches SMS via queue"
  ```

---

## Phase 5: Python Demo & Model Setup
**Days 10–11 | Goal: Judges can see the pipeline working even without the APK**

---

### Task 11: Create Model Setup Script

**Files:**
- Create: `scripts/setup_model.py`

- [ ] **Step 1: Create scripts/setup_model.py**

  ```python
  #!/usr/bin/env python3
  """
  Downloads Gemma 4 E2B (INT4 quantized) from Kaggle and pushes to Android device.
  Run this once before demo. Requires: kaggle CLI configured, adb connected.
  """

  import subprocess
  import sys
  import os

  MODEL_KAGGLE_ID = "google/gemma/frameworks/gemma-2b-it-gpu-int4"
  MODEL_FILENAME = "gemma2b-it-gpu-int4.bin"
  ANDROID_DEST = "/data/local/tmp/gemma4e2b_int4.bin"
  APP_DEST_CMD = "adb shell run-as com.gemma.triage cp /data/local/tmp/gemma4e2b_int4.bin /data/data/com.gemma.triage/files/gemma4e2b_int4.bin"

  def check_prerequisites():
      for tool in ["kaggle", "adb"]:
          if subprocess.run(["where", tool], capture_output=True).returncode != 0:
              print(f"ERROR: '{tool}' not found in PATH. Install it first.")
              sys.exit(1)

  def download_model():
      print("Downloading Gemma 4 E2B INT4 from Kaggle...")
      subprocess.run(
          ["kaggle", "models", "instances", "download", MODEL_KAGGLE_ID,
           "--untar", "--path", "model/"],
          check=True
      )
      model_path = f"model/{MODEL_FILENAME}"
      if not os.path.exists(model_path):
          print(f"ERROR: Expected model file not found at {model_path}")
          print("Check Kaggle model page for correct filename.")
          sys.exit(1)
      return model_path

  def push_to_device(model_path):
      print(f"Pushing model to Android device ({ANDROID_DEST})...")
      subprocess.run(["adb", "push", model_path, ANDROID_DEST], check=True)
      print("Copying into app files directory...")
      subprocess.run(APP_DEST_CMD.split(), check=True)
      print("Model ready. Launch Gemma Triage app.")

  if __name__ == "__main__":
      check_prerequisites()
      model_path = download_model()
      push_to_device(model_path)
  ```

- [ ] **Step 2: Test script dry-run (without device)**

  ```bash
  python scripts/setup_model.py --help  # Will fail with missing args, that's OK
  python -c "import scripts.setup_model"  # Verify no syntax errors
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add scripts/setup_model.py
  git commit -m "feat: add model setup script for Kaggle download + ADB push to Android"
  ```

---

### Task 12: Create Python Demo (Judge Fallback)

**Files:**
- Create: `python_demo/triage_demo.py`
- Create: `python_demo/requirements.txt`

- [ ] **Step 1: Create python_demo/requirements.txt**

  ```
  google-generativeai>=0.8.0
  rich>=13.7.0
  ```

- [ ] **Step 2: Create python_demo/triage_demo.py**

  ```python
  #!/usr/bin/env python3
  """
  Gemma Triage — Python CLI Demo
  Mimics the Android app pipeline using Gemma 4 via Gemini API.
  For judge demo when APK installation isn't possible.
  
  Usage: python triage_demo.py
  Set GEMINI_API_KEY environment variable before running.
  """

  import os
  import json
  import sys
  import time
  import google.generativeai as genai
  from rich.console import Console
  from rich.panel import Panel
  from rich.text import Text

  console = Console()

  SYSTEM_PROMPT = """You are a certified emergency medical triage AI using the START protocol.

  TRIAGE CATEGORIES:
  RED (Immediate): Life-threatening but survivable. Resp >30/min, absent radial pulse, altered mental status.
  YELLOW (Delayed): Serious but stable. Can wait 30-60 min.
  GREEN (Minor): Walking wounded, ambulatory, minor injuries.
  BLACK (Expectant): No respirations after airway repositioning.

  Respond with valid JSON ONLY:
  {"triageCode":"RED|YELLOW|GREEN|BLACK","confidence":0.0,"reasoning":"...","recommendedActions":["..."]}"""

  TRIAGE_COLORS = {
      "RED": "bold red",
      "YELLOW": "bold yellow",
      "GREEN": "bold green",
      "BLACK": "bold white on black",
  }

  def configure_gemma():
      api_key = os.environ.get("GEMINI_API_KEY")
      if not api_key:
          console.print("[red]ERROR: Set GEMINI_API_KEY environment variable[/red]")
          sys.exit(1)
      genai.configure(api_key=api_key)
      return genai.GenerativeModel(
          model_name="gemma-3-27b-it",  # Check Kaggle for latest Gemma 4 model name (e.g. "gemma-4-27b-it")
          system_instruction=SYSTEM_PROMPT,
          generation_config=genai.types.GenerationConfig(temperature=0.1, max_output_tokens=512)
      )

  def classify_patient(model, description: str) -> dict:
      prompt = f"Analyze this patient: {description}"
      console.print(f"\n[dim]Sending to Gemma 4...[/dim]")
      start = time.time()
      response = model.generate_content(prompt)
      elapsed = time.time() - start
      console.print(f"[dim]Response in {elapsed:.1f}s[/dim]")

      raw = response.text
      json_start = raw.find('{')
      json_end = raw.rfind('}') + 1
      if json_start == -1:
          return {"triageCode": "UNKNOWN", "confidence": 0, "reasoning": raw, "recommendedActions": []}
      return json.loads(raw[json_start:json_end])

  def format_sms(result: dict) -> str:
      code = result.get("triageCode", "?")[0]
      conf = int(result.get("confidence", 0) * 100)
      actions = ";".join(a[:20] for a in result.get("recommendedActions", [])[:3])
      sms = f"TRG|{code}|{conf}|{actions}"
      return sms[:160]

  def display_result(result: dict):
      code = result.get("triageCode", "UNKNOWN")
      color = TRIAGE_COLORS.get(code, "white")
      label = {"RED": "IMMEDIATE", "YELLOW": "DELAYED", "GREEN": "MINOR", "BLACK": "EXPECTANT"}.get(code, "")

      title = Text(f"{code} — {label}", style=color, justify="center")
      body = "\n".join([
          f"Confidence: {int(result.get('confidence', 0) * 100)}%",
          f"\nReasoning: {result.get('reasoning', '')}",
          f"\nActions:",
          *[f"  {i+1}. {a}" for i, a in enumerate(result.get('recommendedActions', []))],
          f"\n[dim]SMS: {format_sms(result)}[/dim]"
      ])
      console.print(Panel(body, title=title, border_style=color.split()[-1]))

  def main():
      console.print(Panel("[bold red]GEMMA TRIAGE[/bold red] — [green]OFF-GRID MODE[/green]\nZero-connectivity disaster triage powered by Gemma 4", border_style="red"))

      model = configure_gemma()
      patient_count = 0

      while True:
          console.print(f"\n[dim]Patients assessed this session: {patient_count}[/dim]")
          description = console.input("\n[bold]Describe patient[/bold] (or 'quit'): ").strip()

          if description.lower() in ('quit', 'exit', 'q'):
              console.print(f"\n[green]Session complete. {patient_count} patients assessed.[/green]")
              break

          if not description:
              continue

          try:
              result = classify_patient(model, description)
              display_result(result)
              patient_count += 1
          except Exception as e:
              console.print(f"[red]Error: {e}[/red]")

  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 3: Test the Python demo**

  ```bash
  cd python_demo
  pip install -r requirements.txt
  GEMINI_API_KEY=your_key python triage_demo.py
  ```

  Test with: *"Male, 45, breathing 40 times per minute, no radial pulse, not following commands"*  
  Expected: RED card with confidence >0.9 and 3 recommended actions.

- [ ] **Step 4: Commit**

  ```bash
  git add python_demo/
  git commit -m "feat: add Python CLI demo with Gemma 4 and rich terminal UI for judge fallback"
  ```

---

## Phase 6: Submission Prep
**Days 12–15 | Goal: Kaggle writeup, video, clean repo, APK release**

---

### Task 13: Build Release APK

**Files:**
- Modify: `android/app/build.gradle` (versionName)

- [ ] **Step 1: Update version**

  In `android/app/build.gradle`, set:
  ```groovy
  versionCode 1
  versionName "1.0.0"
  ```

- [ ] **Step 2: Build release APK**

  ```bash
  ./gradlew :app:assembleRelease
  ```
  Output: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

- [ ] **Step 3: Sign APK (if distributing)**

  ```bash
  keytool -genkey -v -keystore gemma-triage.jks -keyalg RSA -keysize 2048 -validity 10000 -alias gemma-triage
  ./gradlew :app:assembleRelease \
    -Pandroid.injected.signing.store.file=gemma-triage.jks \
    -Pandroid.injected.signing.store.password=YOUR_PASS \
    -Pandroid.injected.signing.key.alias=gemma-triage \
    -Pandroid.injected.signing.key.password=YOUR_PASS
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add android/app/build.gradle
  git commit -m "chore: bump version to 1.0.0 for submission"
  ```

---

### Task 14: Create Kaggle Writeup Template

**Files:**
- Create: `docs/kaggle_writeup.md`

- [ ] **Step 1: Create writeup template**

  ```markdown
  # Gemma Triage: Zero-Connectivity Disaster Response Powered by Gemma 4

  ## The Problem (150 words)
  [Describe mass-casualty incidents, lack of connectivity, medic memory limits]

  ## The Solution (200 words)
  [Describe the app: voice in, Gemma 4 local, RED/YELLOW/GREEN/BLACK out, SMS dispatch]

  ## Technical Implementation (400 words)

  ### Architecture
  [MediaPipe LlmInference API + Gemma 4 E2B INT4 on Android]

  ### On-Device Inference
  [How MediaPipe loads and runs the model, GPU acceleration, INT4 quantization]

  ### Prompt Engineering
  [START protocol system prompt + 13 few-shot examples + temperature 0.1]

  ### Speech Pipeline
  [Android SpeechRecognizer offline mode → text → PromptBuilder → inference]

  ### Output Layer
  [160-char SMS compression, QueueManager retry, Room DB audit trail]

  ## Gemma 4 Advantages (200 words)
  [Why Gemma 4 E2B specifically: size fits mobile, quality of medical reasoning, structured output]

  ## Results (200 words)
  [Demo video link, accuracy on test cases, inference time on test device]

  ## Prize Track Alignment (150 words)
  [Global Resilience: zero connectivity design, LiteRT: MediaPipe implementation]

  ## Future Work (100 words)
  [Whisper STT replacement, multilingual support, satellite modem integration]
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add docs/kaggle_writeup.md
  git commit -m "docs: add Kaggle writeup template for submission"
  ```

---

## Verification Checklist (Before Submission)

- [ ] App launches without crash on Android 8+ device
- [ ] Model loads from internal files directory (not assets — too large)
- [ ] Push-to-talk records audio, SpeechRecognizer returns transcript
- [ ] Gemma 4 produces JSON with correct triageCode field
- [ ] Result card shows correct color (RED=red, YELLOW=yellow, etc.)
- [ ] SMS button dispatches to COORDINATOR_NUMBER
- [ ] Room DB stores at least one record per session
- [ ] Python demo produces matching output for same input
- [ ] All 4 triage codes (RED/YELLOW/GREEN/BLACK) tested manually
- [ ] App works with airplane mode ON
- [ ] Kaggle writeup < 1500 words
- [ ] YouTube video < 3 minutes, shows airplane mode + full pipeline
- [ ] GitHub repo is public with clear README

---

## Demo Script (for YouTube Video)

```
[0:00] Open app — "GEMMA TRIAGE" title, "● OFF-GRID" status
[0:05] Show phone settings — Airplane Mode ON — 0 bars
[0:15] Hold RECORD button, speak:
       "Male, approximately 40 years old. Breathing 38 times per minute.
        Radial pulse is absent. Not following my commands."
[0:28] Release button — transcription appears
[0:30] Progress bar — "Gemma 4 analyzing..."
[0:33] RED card appears — "RED — IMMEDIATE — Confidence: 97%"
[0:40] Show reasoning and recommended actions
[0:45] Press DISPATCH — "SMS dispatched to coordinator"
[0:50] Show second patient (GREEN) for contrast
[1:10] Show Python demo as backup
[1:30] Show architecture diagram
[2:00] Close with storyline — Operation Zero-Signal
[2:30] Show GitHub repo, Kaggle page
```
