package com.ontrack.data.model

import kotlinx.datetime.LocalDate
import kotlinx.datetime.LocalTime

data class Session(
    val id: Long = 0,
    val date: LocalDate,
    val startTime: LocalTime?,
    val durationMinutes: Int,
    val type: SessionType,
    val title: String,
    val notes: String = "",
    val status: SessionStatus = SessionStatus.PLANNED,
    val goalId: Long? = null,
    val plannedMetricsJson: String = "{}",
    val actualMetricsJson: String = "{}",
    val stravaActivityId: Long? = null,
)
