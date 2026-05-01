package com.ontrack.data.db.entities

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import com.ontrack.data.model.SessionType
import kotlinx.datetime.LocalDate
import kotlinx.datetime.LocalTime

@Entity(
    tableName = "sessions",
    indices = [Index("date"), Index("goalId"), Index("status")],
    foreignKeys = [
        ForeignKey(
            entity = GoalEntity::class,
            parentColumns = ["id"],
            childColumns = ["goalId"],
            onDelete = ForeignKey.SET_NULL,
        ),
    ],
)
data class SessionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val date: LocalDate,
    val startTime: LocalTime?,
    val durationMinutes: Int,
    val type: String,
    val title: String,
    val notes: String,
    val status: String,
    val goalId: Long?,
    val plannedMetricsJson: String,
    val actualMetricsJson: String,
    val stravaActivityId: Long?,
) {
    fun toDomain(): Session = Session(
        id = id,
        date = date,
        startTime = startTime,
        durationMinutes = durationMinutes,
        type = SessionType.from(type),
        title = title,
        notes = notes,
        status = SessionStatus.from(status),
        goalId = goalId,
        plannedMetricsJson = plannedMetricsJson,
        actualMetricsJson = actualMetricsJson,
        stravaActivityId = stravaActivityId,
    )

    companion object {
        fun fromDomain(s: Session): SessionEntity = SessionEntity(
            id = s.id,
            date = s.date,
            startTime = s.startTime,
            durationMinutes = s.durationMinutes,
            type = s.type.name,
            title = s.title,
            notes = s.notes,
            status = s.status.name,
            goalId = s.goalId,
            plannedMetricsJson = s.plannedMetricsJson,
            actualMetricsJson = s.actualMetricsJson,
            stravaActivityId = s.stravaActivityId,
        )
    }
}
