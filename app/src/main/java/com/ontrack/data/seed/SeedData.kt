package com.ontrack.data.seed

import com.ontrack.data.model.Category
import com.ontrack.data.model.Goal
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionType
import com.ontrack.data.repository.GoalRepository
import com.ontrack.data.repository.SessionRepository
import com.ontrack.util.Dates
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.DayOfWeek
import kotlinx.datetime.LocalDate
import kotlinx.datetime.LocalTime
import kotlinx.datetime.plus
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Seeds a default 4-week plan that matches the user's stated rhythm:
 *  - Monday evening: martial arts
 *  - Tue / Thu mornings: runs (easy + tempo)
 *  - Sat morning: long run
 *  - Fri evening + Sun morning: climbing
 *  - Tue / Wed / Thu evenings: study blocks
 *  - Sat & Sun afternoons: Claude Code / AIGP study
 *  - Daily lunchtime: 30m professional reading
 */
@Singleton
class SeedData @Inject constructor(
    private val sessionRepo: SessionRepository,
    private val goalRepo: GoalRepository,
) {
    suspend fun seedIfEmpty() {
        if (sessionRepo.count() == 0) {
            val goalIds = seedGoals()
            seedFourWeeks(goalIds)
        }
    }

    private suspend fun seedGoals(): GoalIds {
        val today = Dates.today()
        val tenK = goalRepo.upsert(
            Goal(
                title = "10K under 45 minutes",
                description = "Build aerobic base, add tempo + intervals.",
                category = Category.RUNNING,
                targetDate = today.plus(DatePeriod(months = 3)),
                metric = "10K time",
                targetValue = "45:00",
                currentValue = "—",
            ),
        )
        val v6 = goalRepo.upsert(
            Goal(
                title = "Send V6 outdoors",
                description = "Strength + technique sessions, project a route.",
                category = Category.CLIMBING,
                targetDate = today.plus(DatePeriod(months = 6)),
                metric = "Hardest send",
                targetValue = "V6",
                currentValue = "V4",
            ),
        )
        val aigp = goalRepo.upsert(
            Goal(
                title = "Pass AIGP certification",
                description = "Study modules + practice tests.",
                category = Category.STUDY,
                targetDate = today.plus(DatePeriod(months = 4)),
                metric = "Status",
                targetValue = "Certified",
                currentValue = "In progress",
            ),
        )
        val claude = goalRepo.upsert(
            Goal(
                title = "Ship 3 Claude Code projects",
                description = "Build, document, and share.",
                category = Category.STUDY,
                targetDate = today.plus(DatePeriod(months = 6)),
                metric = "Projects shipped",
                targetValue = "3",
                currentValue = "0",
            ),
        )
        return GoalIds(tenK = tenK, v6 = v6, aigp = aigp, claude = claude)
    }

    private suspend fun seedFourWeeks(g: GoalIds) {
        val weekStart = Dates.startOfWeek(Dates.today())
        val sessions = mutableListOf<Session>()
        for (w in 0 until 4) {
            sessions += weekTemplate(weekStart.plus(DatePeriod(days = w * 7)), g, w)
        }
        sessionRepo.upsertAll(sessions)
    }

    private fun weekTemplate(weekStart: LocalDate, g: GoalIds, weekIndex: Int): List<Session> {
        val days = Dates.weekDays(weekStart).associateBy { it.dayOfWeek }
        val out = mutableListOf<Session>()

        days[DayOfWeek.MONDAY]?.let {
            out += Session(
                date = it,
                startTime = LocalTime(19, 0),
                durationMinutes = 90,
                type = SessionType.MARTIAL_ARTS,
                title = "Martial arts class",
                notes = "Recurring Monday class.",
            )
        }
        days[DayOfWeek.TUESDAY]?.let {
            out += Session(
                date = it,
                startTime = LocalTime(7, 0),
                durationMinutes = 45,
                type = SessionType.EASY_RUN,
                title = "Easy 6km",
                goalId = g.tenK,
                plannedMetricsJson = """{"distance_km":6,"target_pace":"easy","rpe":4}""",
            )
            out += Session(
                date = it,
                startTime = LocalTime(20, 0),
                durationMinutes = 60,
                type = SessionType.STUDY_AIGP,
                title = "AIGP module",
                goalId = g.aigp,
            )
        }
        days[DayOfWeek.WEDNESDAY]?.let {
            out += Session(
                date = it,
                startTime = LocalTime(20, 0),
                durationMinutes = 60,
                type = SessionType.STUDY_GENERAL,
                title = "Study block",
                goalId = g.aigp,
            )
        }
        days[DayOfWeek.THURSDAY]?.let {
            val tempoMinutes = 50 + weekIndex * 5
            out += Session(
                date = it,
                startTime = LocalTime(7, 0),
                durationMinutes = tempoMinutes,
                type = SessionType.TEMPO_RUN,
                title = "Tempo ${4 + weekIndex}km @ threshold",
                goalId = g.tenK,
                plannedMetricsJson = """{"warmup_km":2,"tempo_km":${4 + weekIndex},"cooldown_km":1.5}""",
            )
            out += Session(
                date = it,
                startTime = LocalTime(20, 0),
                durationMinutes = 60,
                type = SessionType.STUDY_AIGP,
                title = "AIGP practice questions",
                goalId = g.aigp,
            )
        }
        days[DayOfWeek.FRIDAY]?.let {
            out += Session(
                date = it,
                startTime = LocalTime(18, 30),
                durationMinutes = 90,
                type = SessionType.BOULDER,
                title = "Bouldering session",
                goalId = g.v6,
                plannedMetricsJson = """{"target_grade":"V4-V5","focus":"power"}""",
            )
        }
        days[DayOfWeek.SATURDAY]?.let {
            val longKm = 10 + weekIndex * 2
            out += Session(
                date = it,
                startTime = LocalTime(8, 30),
                durationMinutes = 70 + weekIndex * 10,
                type = SessionType.LONG_RUN,
                title = "Long run ${longKm}km",
                goalId = g.tenK,
                plannedMetricsJson = """{"distance_km":$longKm,"target_pace":"easy"}""",
            )
            out += Session(
                date = it,
                startTime = LocalTime(14, 0),
                durationMinutes = 120,
                type = SessionType.STUDY_CLAUDE_CODE,
                title = "Claude Code project work",
                goalId = g.claude,
            )
        }
        days[DayOfWeek.SUNDAY]?.let {
            out += Session(
                date = it,
                startTime = LocalTime(10, 0),
                durationMinutes = 90,
                type = SessionType.BOULDER,
                title = "Bouldering session",
                goalId = g.v6,
                plannedMetricsJson = """{"target_grade":"V4-V5","focus":"endurance"}""",
            )
            out += Session(
                date = it,
                startTime = LocalTime(14, 0),
                durationMinutes = 120,
                type = SessionType.STUDY_CLAUDE_CODE,
                title = "Claude Code project work",
                goalId = g.claude,
            )
        }

        // Daily reading (skip Mon — martial arts night)
        days.forEach { (dow, date) ->
            if (dow != DayOfWeek.MONDAY) {
                out += Session(
                    date = date,
                    startTime = LocalTime(12, 30),
                    durationMinutes = 30,
                    type = SessionType.READING,
                    title = "Professional reading",
                )
            }
        }
        return out
    }

    private data class GoalIds(val tenK: Long, val v6: Long, val aigp: Long, val claude: Long)
}
