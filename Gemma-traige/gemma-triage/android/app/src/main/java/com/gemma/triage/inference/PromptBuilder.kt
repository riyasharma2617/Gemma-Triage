package com.gemma.triage.inference

object PromptBuilder {
    
    private const val SYSTEM_PROMPT = """
        You are an expert emergency medical responder AI.
        Follow the START (Simple Triage and Rapid Treatment) protocol strictly.
        Analyze the patient's symptoms and classify into one of four categories:
        - RED (Immediate): Life-threatening, needs immediate intervention.
        - YELLOW (Delayed): Serious, but not immediately life-threatening.
        - GREEN (Minor): "Walking wounded", minor injuries.
        - BLACK (Expectant): Deceased or injuries incompatible with life.
        
        Output valid JSON only matching the schema.
    """

    fun buildPrompt(transcribedText: String): String {
        return "<start_of_turn>system\n${SYSTEM_PROMPT.trimIndent()}<end_of_turn>\n" +
               "<start_of_turn>user\nAnalyze this patient description:\n$transcribedText<end_of_turn>\n" +
               "<start_of_turn>model\n"
    }
}
