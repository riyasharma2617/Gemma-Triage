package com.gemma.triage.storage.models

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "triage_records")
data class TriageRecord(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val timestamp: Long,
    val patientDescription: String,
    val triageCode: String,
    val confidence: Double,
    val isTransmitted: Boolean = false
)
