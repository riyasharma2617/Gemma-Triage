package com.gemma.triage.storage

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import com.gemma.triage.storage.models.TriageRecord

@Dao
interface TriageDao {
    @Insert
    suspend fun insert(record: TriageRecord)

    @Query("SELECT * FROM triage_records ORDER BY timestamp DESC")
    suspend fun getAllRecords(): List<TriageRecord>
}

@Database(entities = [TriageRecord::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun triageDao(): TriageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "triage_database"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
