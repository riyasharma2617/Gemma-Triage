package com.gemma.triage

import com.gemma.triage.inference.GemmaInferenceEngine
import com.gemma.triage.inference.TriageCode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class InferenceTest {

    @Test
    fun `parseTriageResult extracts RED from clean JSON`() {
        val json = """{"triageCode":"RED","confidence":0.95,"reasoning":"High resp rate","recommendedActions":["Oxygen","Transport"]}"""
        val result = GemmaInferenceEngine.parseTriageResultFromJson(json)
        assertEquals(TriageCode.RED, result.triageCode)
        assertEquals(0.95, result.confidence, 0.001)
    }

    @Test
    fun `parseTriageResult handles model preamble before JSON`() {
        val rawOutput = "Sure! Here is the triage assessment:\n{\"triageCode\":\"GREEN\",\"confidence\":0.9,\"reasoning\":\"Ambulatory\",\"recommendedActions\":[\"Tag GREEN\"]}"
        val result = GemmaInferenceEngine.parseTriageResultFromJson(rawOutput)
        assertEquals(TriageCode.GREEN, result.triageCode)
    }

    @Test
    fun `parseTriageResult returns UNKNOWN on malformed output`() {
        val result = GemmaInferenceEngine.parseTriageResultFromJson("I cannot determine the triage code.")
        assertEquals(TriageCode.UNKNOWN, result.triageCode)
    }

    @Test
    fun `parseTriageResult handles BLACK code`() {
        val json = """{"triageCode":"BLACK","confidence":0.99,"reasoning":"No respirations","recommendedActions":["Tag BLACK"]}"""
        val result = GemmaInferenceEngine.parseTriageResultFromJson(json)
        assertEquals(TriageCode.BLACK, result.triageCode)
        assertNotNull(result.reasoning)
    }

    @Test
    fun `parseTriageResult handles expanded schema fields`() {
        val json = """{"triageCode":"RED","confidence":0.97,"reasoning":"Three RED criteria","spokenSummary":"RED. Immediate.","immediateSteps":["Step 1","Step 2"],"monitoringChecklist":["Monitor pulse"],"warningSigns":["If stops breathing"],"smsPayload":"TRG|R|97|Step1;Step2"}"""
        val result = GemmaInferenceEngine.parseTriageResultFromJson(json)
        assertEquals(TriageCode.RED, result.triageCode)
        assertEquals(2, result.immediateSteps.size)
        assertEquals("TRG|R|97|Step1;Step2", result.smsPayload)
    }
}
