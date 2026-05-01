package com.ontrack.data.repository

import com.ontrack.data.db.dao.SessionDao
import com.ontrack.data.db.entities.SessionEntity
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.LocalDate
import kotlinx.datetime.plus
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SessionRepository @Inject constructor(
    private val sessionDao: SessionDao,
) {
    fun observeWeek(weekStart: LocalDate): Flow<List<Session>> =
        sessionDao.observeRange(weekStart, weekStart.plus(DatePeriod(days = 6)))
            .map { it.map(SessionEntity::toDomain) }

    fun observeForDate(date: LocalDate): Flow<List<Session>> =
        sessionDao.observeForDate(date).map { it.map(SessionEntity::toDomain) }

    suspend fun byDateOnce(date: LocalDate): List<Session> =
        sessionDao.observeForDate(date).first().map(SessionEntity::toDomain)

    suspend fun byId(id: Long): Session? = sessionDao.byId(id)?.toDomain()

    suspend fun upsert(session: Session): Long =
        sessionDao.upsert(SessionEntity.fromDomain(session))

    suspend fun upsertAll(sessions: List<Session>): List<Long> =
        sessionDao.upsertAll(sessions.map(SessionEntity::fromDomain))

    suspend fun setStatus(id: Long, status: SessionStatus) =
        sessionDao.setStatus(id, status.name)

    suspend fun reschedule(id: Long, date: LocalDate) =
        sessionDao.reschedule(id, date)

    suspend fun swap(aId: Long, bId: Long) {
        val a = sessionDao.byId(aId) ?: return
        val b = sessionDao.byId(bId) ?: return
        sessionDao.update(a.copy(date = b.date, startTime = b.startTime))
        sessionDao.update(b.copy(date = a.date, startTime = a.startTime))
    }

    suspend fun delete(id: Long) = sessionDao.delete(id)

    suspend fun count(): Int = sessionDao.count()
}
