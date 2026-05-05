package com.gemma.triage.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.Locale

sealed class TTSState {
    object Idle : TTSState()
    data class Speaking(val stage: String) : TTSState()
    object Done : TTSState()
    data class Error(val message: String) : TTSState()
}

class TextToSpeechManager(context: Context) : TextToSpeech.OnInitListener {

    private var tts: TextToSpeech = TextToSpeech(context, this)
    private val _state = MutableStateFlow<TTSState>(TTSState.Idle)
    val state: StateFlow<TTSState> = _state

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts.language = Locale.US
            tts.setSpeechRate(0.85f)
            tts.setPitch(1.0f)
            setupUtteranceListener()
        } else {
            _state.value = TTSState.Error("TTS engine failed to initialise")
        }
    }

    private fun setupUtteranceListener() {
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                _state.value = TTSState.Speaking(utteranceId ?: "")
            }
            override fun onDone(utteranceId: String?) {
                if (utteranceId == "DONE") _state.value = TTSState.Done
            }
            override fun onError(utteranceId: String?) {
                _state.value = TTSState.Error("TTS error on utterance $utteranceId")
            }
        })
    }

    fun speakTriageResult(result: TriageResult) {
        tts.stop()
        speak("${result.triageCode.name}. ${labelFor(result.triageCode)}.", "CODE")
        speak(result.spokenSummary.ifBlank { result.reasoning.take(120) }, "SUMMARY")
        if (result.immediateSteps.isEmpty()) {
            speak("No immediate steps specified.", "DONE")
        } else {
            result.immediateSteps.forEachIndexed { i, step ->
                speak(step, if (i == result.immediateSteps.lastIndex) "DONE" else "STEP_$i")
            }
        }
    }

    fun speakFollowUpAnswer(answer: String) {
        tts.stop()
        speak(answer, "DONE")
    }

    fun speak(text: String, utteranceId: String) {
        tts.speak(text, TextToSpeech.QUEUE_ADD, null, utteranceId)
    }

    fun stop() {
        tts.stop()
        _state.value = TTSState.Idle
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }

    private fun labelFor(code: TriageCode) = when (code) {
        TriageCode.RED    -> "Immediate."
        TriageCode.YELLOW -> "Delayed."
        TriageCode.GREEN  -> "Minor."
        TriageCode.BLACK  -> "Expectant."
        TriageCode.UNKNOWN -> "Unknown."
    }
}
