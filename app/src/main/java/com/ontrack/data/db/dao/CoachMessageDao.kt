package com.ontrack.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.ontrack.data.db.entities.CoachMessageEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CoachMessageDao {
    @Query("SELECT * FROM coach_messages ORDER BY createdAt ASC")
    fun observeAll(): Flow<List<CoachMessageEntity>>

    @Query("SELECT * FROM coach_messages ORDER BY createdAt ASC")
    suspend fun all(): List<CoachMessageEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(message: CoachMessageEntity): Long

    @Query("DELETE FROM coach_messages")
    suspend fun clear()
}
