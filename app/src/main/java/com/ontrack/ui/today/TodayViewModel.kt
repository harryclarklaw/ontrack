package com.ontrack.ui.today

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import com.ontrack.data.repository.SessionRepository
import com.ontrack.util.Dates
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.datetime.LocalDate
import javax.inject.Inject

data class TodayUi(
    val date: LocalDate,
    val sessions: List<Session>,
)

@HiltViewModel
class TodayViewModel @Inject constructor(
    private val sessionRepo: SessionRepository,
) : ViewModel() {

    private val today = Dates.today()

    val state: StateFlow<TodayUi> =
        sessionRepo.observeForDate(today)
            .map { TodayUi(today, it) }
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5_000),
                initialValue = TodayUi(today, emptyList()),
            )

    fun complete(id: Long) = update(id, SessionStatus.COMPLETED)
    fun skip(id: Long) = update(id, SessionStatus.SKIPPED)

    private fun update(id: Long, status: SessionStatus) {
        viewModelScope.launch { sessionRepo.setStatus(id, status) }
    }
}
