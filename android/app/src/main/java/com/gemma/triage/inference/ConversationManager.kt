package com.gemma.triage.inference

data class ConversationTurn(val role: String, val text: String)

class ConversationManager {

    private val history = mutableListOf<ConversationTurn>()
    private var patientDescription: String = ""
    private var initialResult: TriageResult? = null

    fun startNewPatient(description: String, result: TriageResult) {
        history.clear()
        patientDescription = description
        initialResult = result
    }

    fun addTurn(role: String, text: String) {
        history.add(ConversationTurn(role, text))
    }

    fun buildFollowUpPrompt(question: String): String {
        val result = initialResult ?: return question
        return buildString {
            append("<start_of_turn>system\n")
            append("You are an emergency medical triage AI assisting a field medic.\n")
            append("Answer follow-up questions about the current patient clearly and concisely.\n")
            append("Think step by step through the patient's condition, the constraint or new ")
            append("information stated, and clinically appropriate alternatives before answering.\n")
            append("Use plain language. No jargon. Maximum 4 sentences.\n")
            append("<end_of_turn>\n")

            append("<start_of_turn>user\n")
            append("Current patient: $patientDescription\n")
            append("Triage classification: ${result.triageCode} (confidence ${(result.confidence * 100).toInt()}%)\n")
            append("Reasoning: ${result.reasoning}\n")
            append("<end_of_turn>\n")
            append("<start_of_turn>model\nUnderstood. Ready for follow-up questions.<end_of_turn>\n")

            for (turn in history) {
                val role = if (turn.role == "user") "user" else "model"
                append("<start_of_turn>$role\n${turn.text}<end_of_turn>\n")
            }

            append("<start_of_turn>user\n$question<end_of_turn>\n")
            append("<start_of_turn>model\n")
        }
    }

    fun isNextPatientCommand(text: String): Boolean {
        val lower = text.lowercase()
        return lower.contains("next patient") || lower.contains("new patient") ||
               lower.contains("next case") || lower == "done" || lower == "next"
    }

    fun hasHistory() = history.isNotEmpty()
    fun turnCount() = history.size
    fun clear() { history.clear(); patientDescription = ""; initialResult = null }
}
