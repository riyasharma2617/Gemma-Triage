package com.gemma.triage.inference

/**
 * Data classes representing the structured JSON output from Gemma.
 */

data class TriageResult(
    val triageCode: TriageCode,
    val confidence: Double,
    val reasoning: String,
    val recommendedActions: List<String>
)

enum class TriageCode {
    RED,
    YELLOW,
    GREEN,
    BLACK,
    UNKNOWN
}
