package com.ontrack.data.db.entities

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.ontrack.data.model.Category
import com.ontrack.data.model.Goal
import kotlinx.datetime.LocalDate

@Entity(tableName = "goals")
data class GoalEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    val description: String,
    val category: String,
    val targetDate: LocalDate,
    val metric: String,
    val targetValue: String,
    val currentValue: String,
    val active: Boolean,
) {
    fun toDomain(): Goal = Goal(
        id = id,
        title = title,
        description = description,
        category = Category.from(category),
        targetDate = targetDate,
        metric = metric,
        targetValue = targetValue,
        currentValue = currentValue,
        active = active,
    )

    companion object {
        fun fromDomain(g: Goal): GoalEntity = GoalEntity(
            id = g.id,
            title = g.title,
            description = g.description,
            category = g.category.name,
            targetDate = g.targetDate,
            metric = g.metric,
            targetValue = g.targetValue,
            currentValue = g.currentValue,
            active = g.active,
        )
    }
}
