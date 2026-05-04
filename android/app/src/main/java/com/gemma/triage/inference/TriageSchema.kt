package com.gemma.triage.inference

data class TriageResult(
    val triageCode: TriageCode,
    val confidence: Double,
    val reasoning: String,
    val spokenSummary: String = "",
    val immediateSteps: List<String> = emptyList(),
    val monitoringChecklist: List<String> = emptyList(),
    val warningSigns: List<String> = emptyList(),
    val smsPayload: String = "",
    val recommendedActions: List<String> = emptyList()
)

enum class TriageCode {
    RED, YELLOW, GREEN, BLACK, UNKNOWN
}

data class RawTriageResult(
    val triageCode: String = "UNKNOWN",
    val confidence: Double = 0.0,
    val reasoning: String = "",
    val spokenSummary: String = "",
    val immediateSteps: List<String> = emptyList(),
    val monitoringChecklist: List<String> = emptyList(),
    val warningSigns: List<String> = emptyList(),
    val smsPayload: String = "",
    val recommendedActions: List<String> = emptyList()
)
