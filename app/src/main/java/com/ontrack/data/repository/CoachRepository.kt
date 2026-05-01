package com.ontrack.data.repository

import com.ontrack.data.db.dao.CoachMessageDao
import com.ontrack.data.db.entities.CoachMessageEntity
import com.ontrack.data.model.CoachMessage
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CoachRepository @Inject constructor(
    private val dao: CoachMessageDao,
) {
    fun observeMessages(): Flow<List<CoachMessage>> =
        dao.observeAll().map { list -> list.map { it.toDomain() } }

    suspend fun all(): List<CoachMessage> =
        dao.all().map { it.toDomain() }

    suspend fun add(message: CoachMessage): Long =
        dao.insert(CoachMessageEntity.fromDomain(message))

    suspend fun clear() = dao.clear()
}
