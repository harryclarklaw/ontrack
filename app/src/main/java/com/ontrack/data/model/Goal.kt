package com.ontrack.data.model

import kotlinx.datetime.LocalDate

data class Goal(
    val id: Long = 0,
    val title: String,
    val description: String,
    val category: Category,
    val targetDate: LocalDate,
    val metric: String,
    val targetValue: String,
    val currentValue: String = "",
    val active: Boolean = true,
)
