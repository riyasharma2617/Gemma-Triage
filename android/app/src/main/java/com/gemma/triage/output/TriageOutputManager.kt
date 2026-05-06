package com.gemma.triage.output

import android.content.Context
import android.telephony.SmsManager
import com.gemma.triage.inference.TriageResult
import com.gemma.triage.storage.AppDatabase
import com.gemma.triage.storage.models.TriageRecord
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class TriageOutputManager private constructor(
    private val coordinatorPhone: String,
    private val smsSender: (phone: String, message: String) -> Unit,
    private val dbWriter: (record: TriageRecord) -> Unit
) {
    private val queueManager = QueueManager(coordinatorPhone, smsSender)

    constructor(
        context: Context,
        coordinatorPhone: String = "5555"
    ) : this(
        coordinatorPhone = coordinatorPhone,
        smsSender = { phone, msg ->
            SmsManager.getDefault().sendTextMessage(phone, null, msg, null, null)
        },
        dbWriter = { record ->
            CoroutineScope(Dispatchers.IO).launch {
                AppDatabase.getDatabase(context).triageDao().insert(record)
            }
        }
    )

    fun process(result: TriageResult, transcription: String) {
        val record = TriageRecord(
            timestamp = System.currentTimeMillis(),
            triageCode = result.triageCode.name,
            confidence = result.confidence,
            transcription = transcription,
            smsPayload = SMSFormatter.formatForSMS(result),
            isTransmitted = false
        )
        dbWriter(record)
        queueManager.enqueue(result)
        queueManager.processQueue()
    }

    companion object {
        operator fun invoke(
            coordinatorPhone: String,
            smsSender: (phone: String, message: String) -> Unit,
            dbWriter: (record: TriageRecord) -> Unit
        ): TriageOutputManager = TriageOutputManager(coordinatorPhone, smsSender, dbWriter)
    }
}
