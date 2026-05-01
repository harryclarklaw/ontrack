package com.ontrack.ui.theme

import androidx.compose.ui.graphics.Color
import com.ontrack.data.model.Category

fun Category.color(): Color = when (this) {
    Category.RUNNING -> CatRunning
    Category.CLIMBING -> CatClimbing
    Category.MARTIAL_ARTS -> CatMartial
    Category.STUDY -> CatStudy
    Category.READING -> CatReading
    Category.REST -> CatRest
}
