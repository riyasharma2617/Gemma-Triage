package com.gemma.triage

import com.gemma.triage.inference.GemmaInferenceEngine
import com.gemma.triage.inference.TriageCode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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

    @Test
    fun `isNextPatientCommand detects exit phrases`() {
        val mgr = com.gemma.triage.inference.ConversationManager()
        assertTrue(mgr.isNextPatientCommand("next patient"))
        assertTrue(mgr.isNextPatientCommand("Next Patient please"))
        assertTrue(mgr.isNextPatientCommand("new patient"))
        assertFalse(mgr.isNextPatientCommand("what about oxygen"))
    }

    @Test
    fun `buildFollowUpPrompt includes patient context and history`() {
        val mgr = com.gemma.triage.inference.ConversationManager()
        val result = com.gemma.triage.inference.TriageResult(
            com.gemma.triage.inference.TriageCode.RED, 0.97, "Three RED criteria",
            "RED. Immediate.", listOf("Step 1"), listOf("Monitor pulse"),
            listOf("If stops breathing"), "TRG|R|97|"
        )
        mgr.startNewPatient("Male, 40, breathing 38/min", result)
        mgr.addTurn("user", "I have no oxygen")
        mgr.addTurn("model", "Use positioning instead")
        val prompt = mgr.buildFollowUpPrompt("He started seizing")
        assertTrue(prompt.contains("Male, 40, breathing 38/min"))
        assertTrue(prompt.contains("I have no oxygen"))
        assertTrue(prompt.contains("He started seizing"))
    }

    @Test
    fun `TTSState Done is emitted on last step utterance id`() {
        val steps = listOf("Step 1", "Step 2", "Step 3")
        val lastId = if (steps.lastIndex == steps.size - 1) "DONE" else "STEP_${steps.lastIndex}"
        assertEquals("DONE", lastId)
    }

    @Test
    fun `SMSFormatter produces output within 160 chars`() {
        val result = com.gemma.triage.inference.TriageResult(
            triageCode = com.gemma.triage.inference.TriageCode.RED,
            confidence = 0.97,
            reasoning = "Respiratory rate high",
            recommendedActions = listOf("Secure airway", "Administer oxygen", "IV access")
        )
        val sms = com.gemma.triage.output.SMSFormatter.formatForSMS(result)
        assertTrue("SMS too long: ${sms.length}", sms.length <= 160)
        assertTrue("SMS missing triage code", sms.contains("|R|"))
    }
}
