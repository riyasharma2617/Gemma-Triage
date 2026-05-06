package com.gemma.triage

import com.gemma.triage.inference.TriageCode
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.output.QueueManager
import com.gemma.triage.output.TriageOutputManager
import com.gemma.triage.storage.models.TriageRecord
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class OutputLayerTest {

    // ─── QueueManager tests ───────────────────────────────────────────────────

    private val sentMessages = mutableListOf<Pair<String, String>>()
    private lateinit var queue: QueueManager

    @Before
    fun setUp() {
        sentMessages.clear()
        queue = QueueManager(
            coordinatorPhone = "+10000000000",
            smsSender = { phone, msg -> sentMessages.add(phone to msg) }
        )
    }

    @Test
    fun `enqueue adds item to queue`() {
        val result = makeResult(TriageCode.RED)
        queue.enqueue(result)
        assertEquals(1, queue.pendingCount())
    }

    @Test
    fun `processQueue sends SMS and clears queue`() {
        val result = makeResult(TriageCode.GREEN)
        queue.enqueue(result)
        queue.processQueue()
        assertEquals(1, sentMessages.size)
        assertEquals(0, queue.pendingCount())
    }

    @Test
    fun `processQueue SMS starts with TRG prefix`() {
        queue.enqueue(makeResult(TriageCode.YELLOW))
        queue.processQueue()
        assertTrue(sentMessages[0].second.startsWith("TRG|"))
    }

    @Test
    fun `processQueue SMS is within 160 chars`() {
        queue.enqueue(makeResult(TriageCode.RED))
        queue.processQueue()
        val msg = sentMessages[0].second
        assertTrue("SMS too long: ${msg.length}", msg.length <= 160)
    }

    @Test
    fun `processQueue does not re-send already sent items`() {
        queue.enqueue(makeResult(TriageCode.BLACK))
        queue.processQueue()   // sends
        queue.processQueue()   // already sent — no re-send
        assertEquals(1, sentMessages.size)
    }

    @Test
    fun `retryFailed re-enqueues failed items`() {
        val failingQueue = QueueManager(
            coordinatorPhone = "+10000000000",
            smsSender = { _, _ -> throw RuntimeException("network error") }
        )
        failingQueue.enqueue(makeResult(TriageCode.RED))
        failingQueue.processQueue()           // fails
        assertEquals(0, failingQueue.pendingCount())  // removed from pending
        assertEquals(1, failingQueue.failedCount())   // added to failed

        // Now retry with a working sender
        val retriedMessages = mutableListOf<Pair<String, String>>()
        failingQueue.updateSmsSender { phone, msg -> retriedMessages.add(phone to msg) }
        failingQueue.retryFailed()
        assertEquals(1, retriedMessages.size)
        assertEquals(0, failingQueue.failedCount())
    }

    @Test
    fun `enqueue multiple results queues all`() {
        queue.enqueue(makeResult(TriageCode.RED))
        queue.enqueue(makeResult(TriageCode.YELLOW))
        queue.enqueue(makeResult(TriageCode.GREEN))
        assertEquals(3, queue.pendingCount())
        queue.processQueue()
        assertEquals(3, sentMessages.size)
    }

    // ─── TriageOutputManager tests ────────────────────────────────────────────

    @Test
    fun `process calls smsSender exactly once`() {
        val smsSent = mutableListOf<String>()
        val mgr = TriageOutputManager(
            coordinatorPhone = "+10000000000",
            smsSender = { _, msg -> smsSent.add(msg) },
            dbWriter = { _ -> /* no-op */ }
        )
        mgr.process(makeResult(TriageCode.RED), "patient has trouble breathing")
        assertEquals(1, smsSent.size)
    }

    @Test
    fun `process calls dbWriter with correct triageCode`() {
        val saved = mutableListOf<TriageRecord>()
        val mgr = TriageOutputManager(
            coordinatorPhone = "+10000000000",
            smsSender = { _, _ -> },
            dbWriter = { record -> saved.add(record) }
        )
        mgr.process(makeResult(TriageCode.BLACK), "no signs of life")
        assertEquals(1, saved.size)
        assertEquals("BLACK", saved[0].triageCode)
    }

    @Test
    fun `process saves transcription in record`() {
        val saved = mutableListOf<TriageRecord>()
        val mgr = TriageOutputManager(
            coordinatorPhone = "+10000000000",
            smsSender = { _, _ -> },
            dbWriter = { record -> saved.add(record) }
        )
        mgr.process(makeResult(TriageCode.YELLOW), "patient is walking")
        assertEquals("patient is walking", saved[0].transcription)
    }

    @Test
    fun `process record has correct confidence`() {
        val saved = mutableListOf<TriageRecord>()
        val mgr = TriageOutputManager(
            coordinatorPhone = "+10000000000",
            smsSender = { _, _ -> },
            dbWriter = { record -> saved.add(record) }
        )
        mgr.process(makeResult(TriageCode.RED, confidence = 0.93), "test")
        assertEquals(0.93, saved[0].confidence, 0.001)
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private fun makeResult(code: TriageCode, confidence: Double = 0.9) = TriageResult(
        triageCode = code,
        confidence = confidence,
        reasoning = "test reasoning",
        recommendedActions = listOf("Action A", "Action B")
    )
}
