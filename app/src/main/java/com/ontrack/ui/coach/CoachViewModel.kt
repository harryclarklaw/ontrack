package com.ontrack.ui.coach

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ontrack.data.model.CoachMessage
import com.ontrack.data.model.CoachRole
import com.ontrack.data.repository.CoachRepository
import com.ontrack.data.repository.GoalRepository
import com.ontrack.data.repository.SessionRepository
import com.ontrack.integrations.ai.CoachService
import com.ontrack.util.Dates
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.datetime.Clock
import kotlinx.datetime.DatePeriod
import kotlinx.datetime.plus
import javax.inject.Inject

data class CoachUi(
    val messages: List<CoachMessage>,
    val sending: Boolean = false,
)

@HiltViewModel
class CoachViewModel @Inject constructor(
    private val coachRepo: CoachRepository,
    private val sessionRepo: SessionRepository,
    private val goalRepo: GoalRepository,
    private val coachService: CoachService,
) : ViewModel() {

    private val sending = MutableStateFlow(false)

    val state: StateFlow<CoachUi> =
        combine(coachRepo.observeMessages(), sending) { messages, isSending ->
            CoachUi(messages = messages, sending = isSending)
        }.stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = CoachUi(emptyList()),
        )

    fun send(text: String) {
        if (text.isBlank()) return
        viewModelScope.launch {
            val now = Clock.System.now()
            coachRepo.add(CoachMessage(role = CoachRole.USER, content = text, createdAt = now))
            sending.value = true
            val history = coachRepo.all()
            val weekStart = Dates.startOfWeek(Dates.today())
            val plan = sessionRepo.observeWeek(weekStart).first() +
                sessionRepo.observeWeek(weekStart.plus(DatePeriod(days = 7))).first()
            val goals = goalRepo.observeGoals().first()
            val reply = runCatching {
                coachService.reply(text, history, plan, goals)
            }.getOrElse {
                CoachMessage(
                    role = CoachRole.ASSISTANT,
                    content = "Coach error: ${it.message ?: "unknown"}",
                    createdAt = Clock.System.now(),
                )
            }
            coachRepo.add(reply)
            sending.value = false
        }
    }

    fun clear() {
        viewModelScope.launch { coachRepo.clear() }
    }
}
