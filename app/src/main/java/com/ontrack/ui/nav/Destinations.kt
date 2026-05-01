package com.ontrack.ui.nav

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.Today
import androidx.compose.ui.graphics.vector.ImageVector

sealed class Destination(val route: String, val label: String, val icon: ImageVector) {
    data object Plan : Destination("plan", "Plan", Icons.Filled.CalendarMonth)
    data object Today : Destination("today", "Today", Icons.Filled.Today)
    data object Goals : Destination("goals", "Goals", Icons.Filled.Flag)
    data object Coach : Destination("coach", "Coach", Icons.Filled.Chat)

    companion object {
        val tabs = listOf(Today, Plan, Goals, Coach)
    }
}
