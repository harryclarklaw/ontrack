package com.ontrack.integrations.strava

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

@Serializable
data class StravaTokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String,
    @SerialName("expires_at") val expiresAt: Long,
    @SerialName("athlete") val athlete: StravaAthlete? = null,
)

@Serializable
data class StravaAthlete(
    val id: Long,
    val firstname: String? = null,
    val lastname: String? = null,
)

@Serializable
data class StravaActivity(
    val id: Long,
    val name: String,
    val type: String,
    @SerialName("sport_type") val sportType: String? = null,
    @SerialName("start_date_local") val startDateLocal: String,
    @SerialName("distance") val distanceMeters: Double,
    @SerialName("moving_time") val movingTimeSeconds: Int,
    @SerialName("average_heartrate") val averageHeartRate: Double? = null,
    @SerialName("average_speed") val averageSpeedMps: Double? = null,
)

interface StravaAuthApi {
    @FormUrlEncoded
    @POST("oauth/token")
    suspend fun exchange(
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("code") code: String,
        @Field("grant_type") grantType: String = "authorization_code",
    ): StravaTokenResponse

    @FormUrlEncoded
    @POST("oauth/token")
    suspend fun refresh(
        @Field("client_id") clientId: String,
        @Field("client_secret") clientSecret: String,
        @Field("refresh_token") refreshToken: String,
        @Field("grant_type") grantType: String = "refresh_token",
    ): StravaTokenResponse
}

interface StravaApi {
    @GET("athlete/activities")
    suspend fun listActivities(
        @Header("Authorization") bearer: String,
        @Query("after") afterEpoch: Long? = null,
        @Query("per_page") perPage: Int = 30,
    ): List<StravaActivity>
}
