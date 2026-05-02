package com.ontrack.data.repository

import com.ontrack.data.db.dao.GoalDao
import com.ontrack.data.db.entities.GoalEntity
import com.ontrack.data.model.Goal
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class GoalRepository @Inject constructor(
    private val goalDao: GoalDao,
) {
    fun observeGoals(): Flow<List<Goal>> =
        goalDao.observeAll().map { list -> list.map { it.toDomain() } }

    suspend fun observeGoalsOnce(): List<Goal> =
        goalDao.observeAll().first().map { it.toDomain() }

    suspend fun byId(id: Long): Goal? = goalDao.byId(id)?.toDomain()

    suspend fun upsert(goal: Goal): Long = goalDao.upsert(GoalEntity.fromDomain(goal))

    suspend fun delete(id: Long) = goalDao.delete(id)
}
