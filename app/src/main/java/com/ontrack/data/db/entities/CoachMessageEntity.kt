package com.ontrack.data.db.entities

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.ontrack.data.model.CoachMessage
import com.ontrack.data.model.CoachRole
import kotlinx.datetime.Instant

@Entity(tableName = "coach_messages")
data class CoachMessageEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val role: String,
    val content: String,
    val createdAt: Instant,
) {
    fun toDomain(): CoachMessage = CoachMessage(
        id = id,
        role = CoachRole.valueOf(role),
        content = content,
        createdAt = createdAt,
    )

    companion object {
        fun fromDomain(m: CoachMessage): CoachMessageEntity = CoachMessageEntity(
            id = m.id,
            role = m.role.name,
            content = m.content,
            createdAt = m.createdAt,
        )
    }
}
