package com.ontrack.ui.plan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import com.ontrack.data.repository.SessionRepository
import com.ontrack.integrations.strava.StravaSync
import com.ontrack.util.Dates
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.LocalDate
import kotlinx.datetime.minus
import kotlinx.datetime.plus
import javax.inject.Inject

data class PlanUi(
    val weekStart: LocalDate,
    val sessions: List<Session>,
    val syncing: Boolean = false,
    val syncMessage: String? = null,
)

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class PlanViewModel @Inject constructor(
    private val sessionRepo: SessionRepository,
    private val stravaSync: StravaSync,
) : ViewModel() {

    private val weekStart = MutableStateFlow(Dates.startOfWeek(Dates.today()))
    private val syncing = MutableStateFlow(false)
    private val syncMessage = MutableStateFlow<String?>(null)

    val state: StateFlow<PlanUi> = weekStart
        .flatMapLatest { ws ->
            kotlinx.coroutines.flow.combine(
                sessionRepo.observeWeek(ws),
                syncing,
                syncMessage,
            ) { sessions, isSyncing, msg ->
                PlanUi(weekStart = ws, sessions = sessions, syncing = isSyncing, syncMessage = msg)
            }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = PlanUi(weekStart = weekStart.value, sessions = emptyList()),
        )

    fun nextWeek() {
        weekStart.value = weekStart.value.plus(DatePeriod(days = 7))
    }

    fun previousWeek() {
        weekStart.value = weekStart.value.minus(DatePeriod(days = 7))
    }

    fun thisWeek() {
        weekStart.value = Dates.startOfWeek(Dates.today())
    }

    fun setStatus(id: Long, status: SessionStatus) {
        viewModelScope.launch { sessionRepo.setStatus(id, status) }
    }

    fun syncStrava() {
        viewModelScope.launch {
            syncing.value = true
            syncMessage.value = null
            val updated = runCatching { stravaSync.syncRecent() }.getOrDefault(0)
            syncing.value = false
            syncMessage.value = if (updated > 0) "Matched $updated session(s) from Strava."
            else "No new Strava activities to import."
        }
    }
}
