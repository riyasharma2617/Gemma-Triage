package com.gemma.triage.storage.models

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "triage_records")
data class TriageRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val timestamp: Long,
    val triageCode: String,
    val confidence: Double,
    val transcription: String,
    val immediateSteps: String,
    val smsPayload: String,
    val isTransmitted: Boolean = false
)
