package com.ontrack

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.lifecycleScope
import com.ontrack.integrations.strava.StravaAuth
import com.ontrack.ui.nav.OnTrackNavHost
import com.ontrack.ui.theme.OnTrackTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var stravaAuth: StravaAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handleStravaCallback(intent)
        setContent {
            OnTrackTheme {
                OnTrackNavHost()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleStravaCallback(intent)
    }

    private fun handleStravaCallback(intent: Intent?) {
        val data = intent?.data ?: return
        if (data.scheme != "ontrack" || data.host != "strava") return
        val code = data.getQueryParameter("code") ?: return
        lifecycleScope.launch { stravaAuth.handleCallback(code) }
    }
}
