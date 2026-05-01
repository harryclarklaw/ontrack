package com.ontrack.integrations.ai

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.Headers
import retrofit2.http.POST

@Serializable
data class AnthropicMessage(val role: String, val content: String)

@Serializable
data class AnthropicRequest(
    val model: String = "claude-sonnet-4-6",
    @SerialName("max_tokens") val maxTokens: Int = 1024,
    val system: String? = null,
    val messages: List<AnthropicMessage>,
)

@Serializable
data class AnthropicContentBlock(val type: String, val text: String? = null)

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
