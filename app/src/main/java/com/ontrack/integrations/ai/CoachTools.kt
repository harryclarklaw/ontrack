package com.ontrack.integrations.ai

import com.ontrack.data.model.Goal
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import com.ontrack.data.model.SessionType
import com.ontrack.data.repository.GoalRepository
import com.ontrack.data.repository.SessionRepository
import com.ontrack.util.Dates
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.LocalDate
import kotlinx.datetime.LocalTime
import kotlinx.datetime.plus
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Tools the in-app coach can invoke. Each tool maps to a repository action.
 * The same definitions can later back an MCP server so Claude Code on a laptop
 * drives the same plan via natural-language chat.
 */
@Singleton
class CoachTools @Inject constructor(
    private val sessionRepo: SessionRepository,
    private val goalRepo: GoalRepository,
) {
    val definitions: List<AnthropicTool> = listOf(
        AnthropicTool(
            name = "get_plan",
            description = "Returns sessions for a week. Default is the current week. " +
                "Pass week_offset (e.g. 1 for next week, -1 for last week).",
            inputSchema = objectSchema(
                properties = mapOf("week_offset" to typeSchema("integer", "Week offset from this week. Defaults to 0.")),
                required = emptyList(),
            ),
        ),
        AnthropicTool(
            name = "get_goals",
            description = "Returns the user's active long-term goals.",
            inputSchema = objectSchema(emptyMap(), emptyList()),
        ),
        AnthropicTool(
            name = "complete_session",
            description = "Marks a session as completed.",
            inputSchema = objectSchema(
                properties = mapOf("session_id" to typeSchema("integer")),
                required = listOf("session_id"),
            ),
        ),
        AnthropicTool(
            name = "skip_session",
            description = "Marks a session as skipped (the user is intentionally not doing it).",
            inputSchema = objectSchema(
                properties = mapOf("session_id" to typeSchema("integer")),
                required = listOf("session_id"),
            ),
        ),
        AnthropicTool(
            name = "reschedule_session",
            description = "Moves a session to a new date (ISO YYYY-MM-DD). Time of day is preserved.",
            inputSchema = objectSchema(
                properties = mapOf(
                    "session_id" to typeSchema("integer"),
                    "new_date" to typeSchema("string", "ISO date, e.g. 2026-05-14"),
                ),
                required = listOf("session_id", "new_date"),
            ),
        ),
        AnthropicTool(
            name = "swap_sessions",
            description = "Swaps the dates and start times of two sessions. " +
                "Use when the user wants to trade two existing sessions.",
            inputSchema = objectSchema(
                properties = mapOf(
                    "session_a_id" to typeSchema("integer"),
                    "session_b_id" to typeSchema("integer"),
                ),
                required = listOf("session_a_id", "session_b_id"),
            ),
        ),
        AnthropicTool(
            name = "add_session",
            description = "Adds a new session. type must be one of: " +
                SessionType.entries.joinToString(", ") { it.name } + ".",
            inputSchema = objectSchema(
                properties = mapOf(
                    "date" to typeSchema("string", "ISO date YYYY-MM-DD"),
                    "type" to typeSchema("string", "SessionType enum name"),
                    "title" to typeSchema("string"),
                    "duration_minutes" to typeSchema("integer"),
                    "start_time" to typeSchema("string", "Optional HH:MM (24h)"),
                    "notes" to typeSchema("string", "Optional"),
                    "goal_id" to typeSchema("integer", "Optional goal id"),
                ),
                required = listOf("date", "type", "title", "duration_minutes"),
            ),
        ),
        AnthropicTool(
            name = "delete_session",
            description = "Removes a session by id.",
            inputSchema = objectSchema(
                properties = mapOf("session_id" to typeSchema("integer")),
                required = listOf("session_id"),
            ),
        ),
        AnthropicTool(
            name = "update_session_notes",
            description = "Replaces the notes field on a session (e.g. workout breakdown, RPE).",
            inputSchema = objectSchema(
                properties = mapOf(
                    "session_id" to typeSchema("integer"),
                    "notes" to typeSchema("string"),
                ),
                required = listOf("session_id", "notes"),
            ),
        ),
    )

    suspend fun execute(name: String, input: JsonObject): String = when (name) {
        "get_plan" -> getPlan(input["week_offset"]?.jsonPrimitive?.content?.toIntOrNull() ?: 0)
        "get_goals" -> getGoals()
        "complete_session" -> setStatus(longArg(input, "session_id"), SessionStatus.COMPLETED)
        "skip_session" -> setStatus(longArg(input, "session_id"), SessionStatus.SKIPPED)
        "reschedule_session" -> reschedule(
            longArg(input, "session_id"),
            stringArg(input, "new_date"),
        )
        "swap_sessions" -> swap(
            longArg(input, "session_a_id"),
            longArg(input, "session_b_id"),
        )
        "add_session" -> addSession(input)
        "delete_session" -> deleteSession(longArg(input, "session_id"))
        "update_session_notes" -> updateNotes(
            longArg(input, "session_id"),
            stringArg(input, "notes"),
        )
        else -> error("Unknown tool: $name")
    }

    private suspend fun getPlan(weekOffset: Int): String {
        val weekStart = Dates.startOfWeek(Dates.today()).plus(DatePeriod(days = weekOffset * 7))
        val sessions = sessionRepo.observeWeekOnce(weekStart)
        return jsonArrayString(sessions.map { it.toToolJson() })
    }

    private suspend fun getGoals(): String {
        val goals = goalRepo.observeGoalsOnce()
        return jsonArrayString(goals.map { it.toToolJson() })
    }

    private suspend fun setStatus(id: Long, status: SessionStatus): String {
        val s = sessionRepo.byId(id) ?: return errorJson("Session $id not found")
        sessionRepo.setStatus(id, status)
        return okJson("Session ${s.title} on ${s.date} marked ${status.name.lowercase()}")
    }

    private suspend fun reschedule(id: Long, newDate: String): String {
        val date = LocalDate.parse(newDate)
        val s = sessionRepo.byId(id) ?: return errorJson("Session $id not found")
        sessionRepo.reschedule(id, date)
        return okJson("Moved ${s.title} from ${s.date} to $date")
    }

    private suspend fun swap(a: Long, b: Long): String {
        val sa = sessionRepo.byId(a) ?: return errorJson("Session $a not found")
        val sb = sessionRepo.byId(b) ?: return errorJson("Session $b not found")
        sessionRepo.swap(a, b)
        return okJson("Swapped ${sa.title} (${sa.date}) with ${sb.title} (${sb.date})")
    }

    private suspend fun addSession(input: JsonObject): String {
        val date = LocalDate.parse(stringArg(input, "date"))
        val typeName = stringArg(input, "type")
        val type = runCatching { SessionType.valueOf(typeName) }.getOrNull()
            ?: return errorJson("Unknown SessionType '$typeName'")
        val title = stringArg(input, "title")
        val durationMinutes = intArg(input, "duration_minutes")
        val startTime = optionalString(input, "start_time")?.let { LocalTime.parse(normalizeTime(it)) }
        val notes = optionalString(input, "notes") ?: ""
        val goalId = optionalLong(input, "goal_id")
        val id = sessionRepo.upsert(
            Session(
                date = date,
                startTime = startTime,
                durationMinutes = durationMinutes,
                type = type,
                title = title,
                notes = notes,
                goalId = goalId,
            ),
        )
        return okJson("Added session $id: $title on $date")
    }

    private suspend fun deleteSession(id: Long): String {
        val s = sessionRepo.byId(id) ?: return errorJson("Session $id not found")
        sessionRepo.delete(id)
        return okJson("Deleted ${s.title} on ${s.date}")
    }

    private suspend fun updateNotes(id: Long, notes: String): String {
        val s = sessionRepo.byId(id) ?: return errorJson("Session $id not found")
        sessionRepo.upsert(s.copy(notes = notes))
        return okJson("Updated notes on ${s.title}")
    }
}

private fun typeSchema(type: String, description: String? = null): JsonObject = buildJsonObject {
    put("type", type)
    if (description != null) put("description", description)
}

private fun objectSchema(properties: Map<String, JsonObject>, required: List<String>): JsonObject =
    buildJsonObject {
        put("type", "object")
        putJsonObject("properties") {
            properties.forEach { (k, v) -> put(k, v) }
        }
        putJsonArray("required") { required.forEach { add(it) } }
    }

private fun longArg(input: JsonObject, key: String): Long =
    input[key]?.jsonPrimitive?.content?.toLong()
        ?: error("Missing integer arg '$key'")

private fun intArg(input: JsonObject, key: String): Int =
    input[key]?.jsonPrimitive?.content?.toInt()
        ?: error("Missing integer arg '$key'")

private fun stringArg(input: JsonObject, key: String): String =
    input[key]?.jsonPrimitive?.content
        ?: error("Missing string arg '$key'")

private fun optionalString(input: JsonObject, key: String): String? =
    input[key]?.jsonPrimitive?.content?.takeIf { it.isNotBlank() }

private fun optionalLong(input: JsonObject, key: String): Long? =
    input[key]?.jsonPrimitive?.content?.toLongOrNull()

private fun normalizeTime(s: String): String =
    if (s.count { it == ':' } == 1) "$s:00" else s

private fun jsonArrayString(items: List<String>): String =
    items.joinToString(prefix = "[", postfix = "]", separator = ",")

private fun okJson(msg: String): String = """{"ok":true,"message":"${msg.escapeJson()}"}"""
private fun errorJson(msg: String): String = """{"ok":false,"error":"${msg.escapeJson()}"}"""

private fun String.escapeJson(): String =
    replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", " ")

private fun Session.toToolJson(): String = buildString {
    append("{")
    append("\"id\":$id,")
    append("\"date\":\"$date\",")
    append("\"start_time\":${startTime?.let { "\"$it\"" } ?: "null"},")
    append("\"duration_minutes\":$durationMinutes,")
    append("\"type\":\"${type.name}\",")
    append("\"title\":\"${title.escapeJson()}\",")
    append("\"status\":\"${status.name}\",")
    append("\"goal_id\":${goalId ?: "null"},")
    append("\"notes\":\"${notes.escapeJson()}\"")
    append("}")
}

private fun Goal.toToolJson(): String = buildString {
    append("{")
    append("\"id\":$id,")
    append("\"title\":\"${title.escapeJson()}\",")
    append("\"category\":\"${category.name}\",")
    append("\"metric\":\"${metric.escapeJson()}\",")
    append("\"current\":\"${currentValue.escapeJson()}\",")
    append("\"target\":\"${targetValue.escapeJson()}\",")
    append("\"target_date\":\"$targetDate\",")
    append("\"active\":$active")
    append("}")
}
