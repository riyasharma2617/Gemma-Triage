package com.gemma.triage.output

import android.telephony.SmsManager
import com.gemma.triage.inference.TriageResult

class QueueManager(
    private val coordinatorPhone: String,
    private var smsSender: ((phone: String, message: String) -> Unit)? = null
) {
    private val pending = ArrayDeque<TriageResult>()
    private val failed = ArrayDeque<TriageResult>()

    fun enqueue(result: TriageResult) {
        pending.addLast(result)
    }

    fun processQueue() {
        val toSend = pending.toList()
        pending.clear()
        for (result in toSend) {
            val sms = SMSFormatter.formatForSMS(result)
            try {
                val sender = smsSender
                if (sender != null) {
                    sender(coordinatorPhone, sms)
                } else {
                    SmsManager.getDefault().sendTextMessage(coordinatorPhone, null, sms, null, null)
                }
            } catch (e: Exception) {
                failed.addLast(result)
            }
        }
    }

    fun retryFailed() {
        val toRetry = failed.toList()
        failed.clear()
        for (result in toRetry) {
            val sms = SMSFormatter.formatForSMS(result)
            try {
                val sender = smsSender
                if (sender != null) {
                    sender(coordinatorPhone, sms)
                } else {
                    SmsManager.getDefault().sendTextMessage(coordinatorPhone, null, sms, null, null)
                }
            } catch (e: Exception) {
                failed.addLast(result)
            }
        }
    }

    fun pendingCount(): Int = pending.size
    fun failedCount(): Int = failed.size

    fun updateSmsSender(newSender: (phone: String, message: String) -> Unit) {
        smsSender = newSender
    }
}
