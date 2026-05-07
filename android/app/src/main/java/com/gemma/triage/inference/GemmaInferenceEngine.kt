package com.gemma.triage.inference

import android.content.Context
import com.google.gson.Gson
import com.google.mediapipe.tasks.genai.llminference.LlmInference
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class GemmaInferenceEngine(private val context: Context) {

    private var llmInference: LlmInference? = null

    suspend fun loadModel(modelPath: String): Boolean = withContext(Dispatchers.IO) {
        val options = LlmInference.LlmInferenceOptions.builder()
            .setModelPath(modelPath)
            .setMaxTokens(512)
            .build()
        llmInference = LlmInference.createFromOptions(context, options)
        true
    }

    suspend fun runTriageInference(patientDescription: String): TriageResult =
        withContext(Dispatchers.IO) {
            val inference = llmInference
                ?: throw IllegalStateException("Model not loaded. Call loadModel() first.")
            val prompt = PromptBuilder.buildPrompt(context, patientDescription)
            val rawOutput = inference.generateResponse(prompt)
            parseTriageResultFromJson(rawOutput)
        }

    suspend fun runFollowUpInference(prompt: String): String = withContext(Dispatchers.IO) {
        val inference = llmInference
            ?: throw IllegalStateException("Model not loaded.")
        val raw = inference.generateResponse(prompt)
        val thinkEnd = raw.indexOf("</thinking>")
        if (thinkEnd != -1) raw.substring(thinkEnd + 11).trim() else raw.trim()
    }

    fun release() {
        llmInference?.close()
        llmInference = null
    }

    companion object {
        private val gson = Gson()

        fun parseTriageResultFromJson(rawOutput: String): TriageResult {
            // Find JSON: if raw output contains '{...}', extract it (handles preamble).
            // If no '{' found, assume model was pre-seeded with '{' and prepend it.
            val jsonStart = rawOutput.indexOf('{')
            val jsonEnd = rawOutput.lastIndexOf('}') + 1
            val (text, start) = if (jsonStart != -1 && jsonEnd > jsonStart) {
                Pair(rawOutput, jsonStart)
            } else {
                val candidate = "{$rawOutput"
                Pair(candidate, 0)
            }
            val end = text.lastIndexOf('}') + 1
            if (end <= start) {
                return TriageResult(TriageCode.UNKNOWN, 0.0, "Model output contained no JSON: $rawOutput")
            }
            return try {
                val jsonStr = text.substring(start, end)
                val raw = gson.fromJson(jsonStr, RawTriageResult::class.java)
                TriageResult(
                    triageCode = try { TriageCode.valueOf(raw.triageCode.uppercase()) }
                                 catch (e: IllegalArgumentException) { TriageCode.UNKNOWN },
                    confidence = raw.confidence.coerceIn(0.0, 1.0),
                    reasoning = raw.reasoning,
                    spokenSummary = raw.spokenSummary.ifBlank { raw.reasoning.take(120) },
                    immediateSteps = raw.immediateSteps,
                    monitoringChecklist = raw.monitoringChecklist,
                    warningSigns = raw.warningSigns,
                    smsPayload = raw.smsPayload.take(160),
                    recommendedActions = raw.recommendedActions
                )
            } catch (e: Exception) {
                TriageResult(TriageCode.UNKNOWN, 0.0, "JSON parse error: ${e.message}")
            }
        }
    }
}
