package com.gemma.triage.output

import com.gemma.triage.inference.TriageResult

/**
 * Formats triage JSON output into highly compressed SMS messages for offline transmission.
 */
object SMSFormatter {
    
    /**
     * Compresses the result to fit within 160 characters.
     * Format: TRG|<CODE>|<CONF>|<ACTION1>...
     */
    fun formatForSMS(result: TriageResult): String {
        val codeStr = result.triageCode.name.take(1) // R, Y, G, B
        val confStr = (result.confidence * 100).toInt().toString()
        val actions = result.recommendedActions.joinToString(";") { it.take(20) }
        
        val sms = "TRG|$codeStr|$confStr|$actions"
        
        // Ensure it fits within standard SMS limits
        return if (sms.length > 160) {
            sms.substring(0, 160)
        } else {
            sms
        }
    }
}
