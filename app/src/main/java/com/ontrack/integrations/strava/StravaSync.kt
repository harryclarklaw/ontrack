package com.ontrack.integrations.strava

import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import com.ontrack.data.model.SessionType
import com.ontrack.data.repository.SessionRepository
import com.ontrack.util.Dates
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.LocalDate
import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.LocalTime
import kotlinx.datetime.TimeZone
import kotlinx.datetime.minus
import kotlinx.datetime.toInstant
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.abs

@Singleton
class StravaSync @Inject constructor(
    private val auth: StravaAuth,
    private val api: StravaApi,
    private val sessionRepo: SessionRepository,
) {
    /**
     * Pulls recent Strava activities and matches them to planned running sessions
     * by date proximity. Marks matched sessions COMPLETED and stores the activity id.
     * Returns the number of sessions that were updated.
     */
    suspend fun syncRecent(daysBack: Int = 14): Int {
        val token = auth.freshAccessToken() ?: return 0
        val since = (Dates.today().minus(DatePeriod(days = daysBack)))
            .toEpochSeconds()
        val activities = runCatching {
            api.listActivities(bearer = "Bearer $token", afterEpoch = since)
        }.getOrNull() ?: return 0

        var updated = 0
        for (activity in activities) {
            if (!activity.isRun()) continue
            val activityDate = activity.startDateLocal.substringBefore('T')
            val date = runCatching { LocalDate.parse(activityDate) }.getOrNull() ?: continue
            val match = nearestRunOn(date) ?: continue
            if (match.stravaActivityId != null) continue
            sessionRepo.upsert(
                match.copy(
                    status = SessionStatus.COMPLETED,
                    stravaActivityId = activity.id,
                    actualMetricsJson = activity.toActualMetricsJson(),
                ),
            )
            updated++
        }
        return updated
    }

    private suspend fun nearestRunOn(date: LocalDate): Session? {
        // Get sessions within +/- 1 day; pick the closest planned run.
        val window = listOf(
            date.minus(DatePeriod(days = 1)),
            date,
            date.plusDays(1),
        )
        val all = window.flatMap { sessionRepo.byDateOnce(it) }
        return all.filter { it.type.isRun() && it.status == SessionStatus.PLANNED }
            .minByOrNull { abs(daysBetween(it.date, date)) }
    }
}

private fun StravaActivity.isRun(): Boolean {
    val t = (sportType ?: type).lowercase()
    return t.contains("run")
}

private fun SessionType.isRun(): Boolean = when (this) {
    SessionType.EASY_RUN, SessionType.TEMPO_RUN, SessionType.LONG_RUN,
    SessionType.INTERVAL_RUN, SessionType.RECOVERY_RUN -> true
    else -> false
}

private fun StravaActivity.toActualMetricsJson(): String {
    val km = "%.2f".format(distanceMeters / 1000.0)
    val minutes = movingTimeSeconds / 60
    val pace = if (distanceMeters > 0) {
        val secPerKm = movingTimeSeconds / (distanceMeters / 1000.0)
        val mm = (secPerKm / 60).toInt()
        val ss = (secPerKm % 60).toInt()
        "%d:%02d/km".format(mm, ss)
    } else "—"
    val hr = averageHeartRate?.toInt()
    return buildString {
        append("{")
        append("\"distance_km\":$km,")
        append("\"duration_min\":$minutes,")
        append("\"avg_pace\":\"$pace\"")
        if (hr != null) append(",\"avg_hr\":$hr")
        append("}")
    }
}

private fun LocalDate.toEpochSeconds(): Long =
    LocalDateTime(this, LocalTime(0, 0))
        .toInstant(TimeZone.currentSystemDefault())
        .epochSeconds

private fun LocalDate.plusDays(n: Int): LocalDate =
    kotlinx.datetime.plus(this, DatePeriod(days = n))

private fun daysBetween(a: LocalDate, b: LocalDate): Int =
    a.toEpochDays() - b.toEpochDays()
