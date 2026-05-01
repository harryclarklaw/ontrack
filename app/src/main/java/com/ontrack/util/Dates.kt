package com.ontrack.util

import kotlinx.datetime.Clock
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.DayOfWeek
import kotlinx.datetime.LocalDate
import kotlinx.datetime.TimeZone
import kotlinx.datetime.minus
import kotlinx.datetime.plus
import kotlinx.datetime.todayIn

object Dates {
    fun today(zone: TimeZone = TimeZone.currentSystemDefault()): LocalDate =
        Clock.System.todayIn(zone)

    fun startOfWeek(date: LocalDate): LocalDate {
        val daysFromMonday = (date.dayOfWeek.isoDayNumber - DayOfWeek.MONDAY.isoDayNumber + 7) % 7
        return date.minus(DatePeriod(days = daysFromMonday))
    }

    fun weekDays(weekStart: LocalDate): List<LocalDate> =
        (0..6).map { weekStart.plus(DatePeriod(days = it)) }

    fun weekRangeLabel(weekStart: LocalDate): String {
        val end = weekStart.plus(DatePeriod(days = 6))
        return "${shortDate(weekStart)} – ${shortDate(end)}"
    }

    fun shortDate(d: LocalDate): String {
        val month = d.month.name.lowercase().replaceFirstChar { it.uppercase() }.take(3)
        return "${d.dayOfMonth} $month"
    }

    fun shortDayName(dow: DayOfWeek): String = when (dow) {
        DayOfWeek.MONDAY -> "Mon"
        DayOfWeek.TUESDAY -> "Tue"
        DayOfWeek.WEDNESDAY -> "Wed"
        DayOfWeek.THURSDAY -> "Thu"
        DayOfWeek.FRIDAY -> "Fri"
        DayOfWeek.SATURDAY -> "Sat"
        DayOfWeek.SUNDAY -> "Sun"
        else -> dow.name.take(3)
    }
}
