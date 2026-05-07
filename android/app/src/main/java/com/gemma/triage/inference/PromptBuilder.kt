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
            append("<start_of_turn>model\n{")
        }
    }

    private fun buildFewShotBlock(context: Context): String {
        val json = loadAsset(context, "prompts/few_shot_examples.json")
        val type = object : TypeToken<List<Map<String, Any>>>() {}.type
        val examples: List<Map<String, Any>> = gson.fromJson(json, type)
        val selected = examples.shuffled().take(1)
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
