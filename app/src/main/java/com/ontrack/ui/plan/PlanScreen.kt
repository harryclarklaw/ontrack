package com.ontrack.ui.plan

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ontrack.data.model.Session
import com.ontrack.data.model.SessionStatus
import com.ontrack.ui.components.EmptyDayRow
import com.ontrack.ui.components.SessionCard
import com.ontrack.util.Dates
import kotlinx.datetime.LocalDate

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlanScreen(
    padding: PaddingValues,
    viewModel: PlanViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        modifier = Modifier.padding(padding),
        topBar = {
            TopAppBar(
                title = { Text("Week of ${Dates.weekRangeLabel(state.weekStart)}") },
                actions = {
                    IconButton(onClick = viewModel::syncStrava) {
                        Icon(Icons.Filled.Sync, contentDescription = "Sync Strava")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                ),
            )
        },
    ) { inner ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(inner),
        ) {
            WeekNav(
                onPrev = viewModel::previousWeek,
                onToday = viewModel::thisWeek,
                onNext = viewModel::nextWeek,
            )
            state.syncMessage?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                )
            }
            Spacer(Modifier.height(4.dp))
            WeekList(
                weekStart = state.weekStart,
                sessions = state.sessions,
                onComplete = { viewModel.setStatus(it, SessionStatus.COMPLETED) },
                onSkip = { viewModel.setStatus(it, SessionStatus.SKIPPED) },
            )
        }
    }
}

@Composable
private fun WeekNav(onPrev: () -> Unit, onToday: () -> Unit, onNext: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        IconButton(onClick = onPrev) {
            Icon(Icons.Filled.ChevronLeft, contentDescription = "Previous week")
        }
        TextButton(onClick = onToday) { Text("This week") }
        IconButton(onClick = onNext) {
            Icon(Icons.Filled.ChevronRight, contentDescription = "Next week")
        }
    }
}

@Composable
private fun WeekList(
    weekStart: LocalDate,
    sessions: List<Session>,
    onComplete: (Long) -> Unit,
    onSkip: (Long) -> Unit,
) {
    val days = Dates.weekDays(weekStart)
    val byDate = sessions.groupBy { it.date }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        days.forEach { date ->
            val dayLabel = "${Dates.shortDayName(date.dayOfWeek)} · ${date.dayOfMonth}"
            item(key = "h-$date") {
                Text(
                    text = dayLabel,
                    style = MaterialTheme.typography.labelLarge,
                    color = if (date == Dates.today()) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 8.dp, bottom = 4.dp),
                )
            }
            val daySessions = byDate[date].orEmpty()
            if (daySessions.isEmpty()) {
                item(key = "empty-$date") { EmptyDayRow("Rest day") }
            } else {
                items(daySessions, key = { it.id }) { session ->
                    SessionCard(
                        session = session,
                        onComplete = { onComplete(session.id) },
                        onSkip = { onSkip(session.id) },
                    )
                }
            }
        }
    }
}
