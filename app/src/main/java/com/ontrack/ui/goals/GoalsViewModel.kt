package com.ontrack.ui.goals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ontrack.data.model.Goal
import com.ontrack.data.repository.GoalRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class GoalsViewModel @Inject constructor(
    private val goalRepo: GoalRepository,
) : ViewModel() {

    val goals: StateFlow<List<Goal>> = goalRepo.observeGoals()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = emptyList(),
        )

    fun upsert(goal: Goal) {
        viewModelScope.launch { goalRepo.upsert(goal) }
    }

    fun delete(id: Long) {
        viewModelScope.launch { goalRepo.delete(id) }
    }
}
