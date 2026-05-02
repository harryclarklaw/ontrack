package com.ontrack.integrations.ai

import com.ontrack.BuildConfig
import com.ontrack.data.model.CoachMessage
import com.ontrack.data.model.CoachRole
import com.ontrack.util.Dates
import kotlinx.datetime.Clock
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CoachService @Inject constructor(
    private val api: AnthropicApi,
    private val tools: CoachTools,
    private val json: Json,
) {
    private val maxIterations = 6

    private fun systemPrompt(): String = """
        You are OnTrack's personal AI coach. The user is balancing running, bouldering,
        martial arts, study (Claude Code, AIGP cert) and professional reading.

        Today is ${Dates.today()}.

        Hard constraints:
        - Monday evening is fixed for martial arts. Never reschedule that.
        - Avoid scheduling two hard run sessions (TEMPO_RUN, INTERVAL_RUN, LONG_RUN) on
          consecutive days.
        - Keep at least one rest day per week.
        - When you replace a missed session, prefer moving it (reschedule_session) over
          adding a duplicate.

        How to work:
        - Always call get_plan first to read fresh state before suggesting or making
          changes. Never assume session ids.
        - Use tools to apply changes the user agrees to. Don't just describe edits in
          prose if the user has clearly asked for them.
        - After making changes, give a short bullet summary of what you did.
        - Be concise. No long monologues. Structured run prescriptions are warmup /
          main / cooldown only.
    """.trimIndent()

    suspend fun reply(userMessage: String, history: List<CoachMessage>): CoachMessage {
        if (BuildConfig.ANTHROPIC_API_KEY.isBlank()) {
            return CoachMessage(
                role = CoachRole.ASSISTANT,
                content = "Coach offline. Set ANTHROPIC_API_KEY in local.properties to enable " +
                    "tool-driven coaching. You said: \"$userMessage\"",
                createdAt = Clock.System.now(),
            )
        }

        val messages = mutableListOf<AnthropicMessage>()
        history.forEach {
            if (it.role == CoachRole.USER || it.role == CoachRole.ASSISTANT) {
                messages += AnthropicMessage(
                    role = it.role.name.lowercase(),
                    content = JsonPrimitive(it.content),
                )
            }
        }
        messages += AnthropicMessage(role = "user", content = JsonPrimitive(userMessage))

        val collectedText = StringBuilder()
        val actionLog = mutableListOf<String>()

        var iter = 0
        while (iter < maxIterations) {
            iter++
            val response = api.messages(
                apiKey = BuildConfig.ANTHROPIC_API_KEY,
                body = AnthropicRequest(
                    system = systemPrompt(),
                    messages = messages,
                    tools = tools.definitions,
                ),
            )

            response.content
                .filter { it.type == "text" && !it.text.isNullOrBlank() }
                .forEach { collectedText.appendLine(it.text!!.trim()) }

            val toolUses = response.content.filter { it.type == "tool_use" }
            if (toolUses.isEmpty()) break

            messages += AnthropicMessage(
                role = "assistant",
                content = json.encodeToJsonElement(
                    ListSerializer(AnthropicContentBlock.serializer()),
                    response.content,
                ),
            )

            val resultBlocks = toolUses.map { use ->
                val name = use.name ?: "unknown"
                val (output, isError) = runCatching {
                    tools.execute(name, use.input ?: buildJsonObject {})
                }.fold(
                    onSuccess = { it to false },
                    onFailure = { """{"ok":false,"error":"${it.message ?: "unknown"}"}""" to true },
                )
                actionLog += "$name → ${if (isError) "error" else "ok"}"
                AnthropicContentBlock(
                    type = "tool_result",
                    toolUseId = use.id,
                    content = output,
                    isError = if (isError) true else null,
                )
            }
            messages += AnthropicMessage(
                role = "user",
                content = json.encodeToJsonElement(
                    ListSerializer(AnthropicContentBlock.serializer()),
                    resultBlocks,
                ),
            )
        }

        return finalize(collectedText, actionLog)
    }

    private fun finalize(text: StringBuilder, actionLog: List<String>): CoachMessage {
        val body = text.toString().trim().ifBlank {
            if (actionLog.isEmpty()) "(no reply)"
            else "Done. Applied: ${actionLog.joinToString(", ")}"
        }
        return CoachMessage(
            role = CoachRole.ASSISTANT,
            content = body,
            createdAt = Clock.System.now(),
        )
    }
}
