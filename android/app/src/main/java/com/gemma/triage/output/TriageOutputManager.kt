package com.gemma.triage.output

import android.content.Context
import android.telephony.SmsManager
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.storage.AppDatabase
import com.gemma.triage.storage.models.TriageRecord
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class TriageOutputManager(
    private val coordinatorPhone: String,
    private val smsSender: (phone: String, message: String) -> Unit,
    private val dbWriter: (record: TriageRecord) -> Unit
) {
    private val queueManager = QueueManager(coordinatorPhone, smsSender)

    fun process(result: TriageResult, transcription: String) {
        val record = TriageRecord(
            timestamp = System.currentTimeMillis(),
            triageCode = result.triageCode.name,
            confidence = result.confidence,
            transcription = transcription,
            smsPayload = SMSFormatter.formatForSMS(result),
            isTransmitted = false // Known limitation: updated to true only when DB callback is wired up
        )
        dbWriter(record)
        queueManager.enqueue(result)
        queueManager.processQueue()
    }

    companion object {
        private val dbScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

        fun create(context: Context, coordinatorPhone: String = "5555"): TriageOutputManager {
            return TriageOutputManager(
                coordinatorPhone = coordinatorPhone,
                smsSender = { phone, msg ->
                    SmsManager.getDefault().sendTextMessage(phone, null, msg, null, null)
                },
                dbWriter = { record ->
                    dbScope.launch {
                        try {
                            AppDatabase.getDatabase(context).triageDao().insert(record)
                        } catch (e: Exception) {
                            android.util.Log.e("TriageOutputManager", "DB insert failed: ${e.message}")
                        }
                    }
                }
            )
        }
    }
}
