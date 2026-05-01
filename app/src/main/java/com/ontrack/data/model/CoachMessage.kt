package com.ontrack.data.model

import kotlinx.datetime.Instant

enum class CoachRole { USER, ASSISTANT, SYSTEM }

data class CoachMessage(
    val id: Long = 0,
    val role: CoachRole,
    val content: String,
    val createdAt: Instant,
)
