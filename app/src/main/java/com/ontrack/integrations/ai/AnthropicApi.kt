package com.ontrack.integrations.ai

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.Headers
import retrofit2.http.POST

@Serializable
data class AnthropicTool(
    val name: String,
    val description: String,
    @SerialName("input_schema") val inputSchema: JsonObject,
)

@Serializable
data class AnthropicMessage(
    val role: String,
    val content: JsonElement,
)

@Serializable
data class AnthropicRequest(
    val model: String = "claude-sonnet-4-6",
    @SerialName("max_tokens") val maxTokens: Int = 2048,
    val system: String? = null,
    val messages: List<AnthropicMessage>,
    val tools: List<AnthropicTool>? = null,
)

@Serializable
data class AnthropicContentBlock(
    val type: String,
    // text block
    val text: String? = null,
    // tool_use block
    val id: String? = null,
    val name: String? = null,
    val input: JsonObject? = null,
    // tool_result block
    @SerialName("tool_use_id") val toolUseId: String? = null,
    val content: String? = null,
    @SerialName("is_error") val isError: Boolean? = null,
)

@Serializable
data class AnthropicResponse(
    val id: String? = null,
    val role: String? = null,
    val model: String? = null,
    val content: List<AnthropicContentBlock> = emptyList(),
    @SerialName("stop_reason") val stopReason: String? = null,
)

interface AnthropicApi {
    @Headers(
        "anthropic-version: 2023-06-01",
        "content-type: application/json",
    )
    @POST("v1/messages")
    suspend fun messages(
        @Header("x-api-key") apiKey: String,
        @Body body: AnthropicRequest,
    ): AnthropicResponse
}
