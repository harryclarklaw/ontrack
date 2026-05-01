package com.ontrack.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.ontrack.data.db.entities.SessionEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.datetime.LocalDate

@Dao
interface SessionDao {
    @Query("SELECT * FROM sessions WHERE date BETWEEN :start AND :end ORDER BY date ASC, startTime ASC")
    fun observeRange(start: LocalDate, end: LocalDate): Flow<List<SessionEntity>>

    @Query("SELECT * FROM sessions WHERE date = :date ORDER BY startTime ASC")
    fun observeForDate(date: LocalDate): Flow<List<SessionEntity>>

    @Query("SELECT * FROM sessions WHERE id = :id LIMIT 1")
    suspend fun byId(id: Long): SessionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(session: SessionEntity): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(sessions: List<SessionEntity>): List<Long>

    @Update
    suspend fun update(session: SessionEntity)

    @Query("UPDATE sessions SET status = :status WHERE id = :id")
    suspend fun setStatus(id: Long, status: String)

    @Query("UPDATE sessions SET date = :date WHERE id = :id")
    suspend fun reschedule(id: Long, date: LocalDate)

    @Query("DELETE FROM sessions WHERE id = :id")
    suspend fun delete(id: Long)

    @Query("SELECT COUNT(*) FROM sessions")
    suspend fun count(): Int
}
