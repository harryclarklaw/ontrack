package com.ontrack.integrations.strava

import android.content.Context
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.ontrack.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "strava_auth")

@Singleton
class StravaAuth @Inject constructor(
    @ApplicationContext private val context: Context,
    private val authApi: StravaAuthApi,
) {
    private val accessKey = stringPreferencesKey("access_token")
    private val refreshKey = stringPreferencesKey("refresh_token")
    private val expiresKey = longPreferencesKey("expires_at")
    private val athleteKey = longPreferencesKey("athlete_id")

    val accessToken: Flow<String?> =
        context.dataStore.data.map { it[accessKey] }

    val isAuthorized: Flow<Boolean> =
        context.dataStore.data.map { !it[accessKey].isNullOrBlank() }

    fun launchAuthFlow() {
        val clientId = BuildConfig.STRAVA_CLIENT_ID
        val redirect = BuildConfig.STRAVA_REDIRECT_URI
        if (clientId.isBlank()) return
        val authUri = Uri.parse("https://www.strava.com/oauth/mobile/authorize")
            .buildUpon()
            .appendQueryParameter("client_id", clientId)
            .appendQueryParameter("redirect_uri", redirect)
            .appendQueryParameter("response_type", "code")
            .appendQueryParameter("approval_prompt", "auto")
            .appendQueryParameter("scope", "read,activity:read_all")
            .build()
        CustomTabsIntent.Builder().build().launchUrl(context, authUri)
    }

    suspend fun handleCallback(code: String): Boolean {
        if (BuildConfig.STRAVA_CLIENT_ID.isBlank() || BuildConfig.STRAVA_CLIENT_SECRET.isBlank()) {
            return false
        }
        return runCatching {
            val token = authApi.exchange(
                clientId = BuildConfig.STRAVA_CLIENT_ID,
                clientSecret = BuildConfig.STRAVA_CLIENT_SECRET,
                code = code,
            )
            persist(token)
            true
        }.getOrDefault(false)
    }

    suspend fun freshAccessToken(): String? {
        val prefs = context.dataStore.data.first()
        val access = prefs[accessKey] ?: return null
        val expires = prefs[expiresKey] ?: 0L
        val nowSeconds = System.currentTimeMillis() / 1000
        if (nowSeconds < expires - 60) return access
        val refresh = prefs[refreshKey] ?: return null
        return runCatching {
            val token = authApi.refresh(
                clientId = BuildConfig.STRAVA_CLIENT_ID,
                clientSecret = BuildConfig.STRAVA_CLIENT_SECRET,
                refreshToken = refresh,
            )
            persist(token)
            token.accessToken
        }.getOrNull()
    }

    suspend fun signOut() {
        context.dataStore.edit { it.clear() }
    }

    private suspend fun persist(token: StravaTokenResponse) {
        context.dataStore.edit {
            it[accessKey] = token.accessToken
            it[refreshKey] = token.refreshToken
            it[expiresKey] = token.expiresAt
            token.athlete?.id?.let { id -> it[athleteKey] = id }
        }
    }
}
