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
