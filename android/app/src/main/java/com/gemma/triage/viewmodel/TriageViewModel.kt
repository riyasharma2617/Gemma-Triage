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
    private val outputManager = TriageOutputManager(context)

    private val _uiState = MutableStateFlow<TriageUiState>(TriageUiState.Idle)
    val uiState: StateFlow<TriageUiState> = _uiState

    private val _patientCount = MutableStateFlow(0)
    val patientCount: StateFlow<Int> = _patientCount

    private val _modelReady = MutableStateFlow(false)
    val modelReady: StateFlow<Boolean> = _modelReady

    private var inFollowUpMode = false
    private var lastQuestion = ""

    init {
        observeSTT()
        observeTTS()
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
