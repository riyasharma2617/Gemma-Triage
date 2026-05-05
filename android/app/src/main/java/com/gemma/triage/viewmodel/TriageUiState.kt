package com.gemma.triage.viewmodel

import com.gemma.triage.inference.TriageResult

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
