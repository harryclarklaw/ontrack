package com.ontrack.integrations.ai

import com.ontrack.BuildConfig
import com.ontrack.data.model.CoachMessage
import com.ontrack.data.model.CoachRole
import com.ontrack.data.model.Goal
import com.ontrack.data.model.Session
import com.ontrack.util.Dates
import kotlinx.datetime.Clock
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CoachService @Inject constructor(
    private val api: AnthropicApi,
) {
    private val systemPrompt = """
        You are OnTrack's personal AI coach. You help the user balance training (running,
        bouldering, martial arts) with study (Claude Code, AIGP cert) and professional reading.
        Constraints: Monday evening is fixed for martial arts. Avoid back-to-back hard run days.
        Keep at least one rest day per week. Replace skipped sessions intelligently.
        Be concise. When proposing changes, list them as bullets with day + session. Never produce
        long monologues. If the user asks for a structured run, output it as warmup / main / cooldown.
    """.trimIndent()

    suspend fun reply(
        userMessage: String,
        history: List<CoachMessage>,
        plan: List<Session>,
        goals: List<Goal>,
    ): CoachMessage {
        val context = buildContext(plan, goals)
        val messages = buildList {
            add(AnthropicMessage(role = "user", content = "Context:\n$context"))
            history.forEach {
                if (it.role == CoachRole.USER || it.role == CoachRole.ASSISTANT) {
                    add(AnthropicMessage(role = it.role.name.lowercase(), content = it.content))
                }
            }
            add(AnthropicMessage(role = "user", content = userMessage))
        }

        val text = if (BuildConfig.ANTHROPIC_API_KEY.isBlank()) {
            stubReply(userMessage)
        } else {
            runCatching {
                api.messages(
                    apiKey = BuildConfig.ANTHROPIC_API_KEY,
                    body = AnthropicRequest(
                        system = systemPrompt,
                        messages = messages,
                    ),
                ).content.firstOrNull { it.type == "text" }?.text
            }.getOrNull() ?: stubReply(userMessage)
        }

        return CoachMessage(role = CoachRole.ASSISTANT, content = text, createdAt = Clock.System.now())
    }

    private fun stubReply(userMessage: String): String =
        "Coach (offline stub): set ANTHROPIC_API_KEY in local.properties to enable live coaching. " +
            "You said: \"$userMessage\""

    private fun buildContext(plan: List<Session>, goals: List<Goal>): String {
        val today = Dates.today()
        val goalLines = goals.joinToString("\n") {
            "- ${it.category.display}: ${it.title} (target ${it.targetValue} by ${it.targetDate})"
        }
        val planLines = plan
            .filter { it.date >= today }
            .take(20)
            .joinToString("\n") {
                "- ${it.date} ${it.startTime ?: ""} ${it.type.display}: ${it.title} [${it.status.display}]"
            }
        return buildString {
            append("Today: $today\n")
            append("Active goals:\n").append(goalLines).append("\n\n")
            append("Upcoming plan:\n").append(planLines)
        }
    }
}
