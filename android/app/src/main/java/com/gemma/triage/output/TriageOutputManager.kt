package com.gemma.triage.output

import android.content.Context
import com.gemma.triage.inference.TriageResult

class TriageOutputManager(private val context: Context) {

    /**
     * Processes a completed triage result: logs to storage, sends SMS if configured.
     * Currently a stub — full implementation in Phase 3.
     */
    fun process(result: TriageResult, transcription: String) {
        // Phase 3: persist to Room database, trigger SMS via SmsManager
    }
}
