package com.ontrack.data.db

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.ontrack.data.db.dao.CoachMessageDao
import com.ontrack.data.db.dao.GoalDao
import com.ontrack.data.db.dao.SessionDao
import com.ontrack.data.db.entities.CoachMessageEntity
import com.ontrack.data.db.entities.GoalEntity
import com.ontrack.data.db.entities.SessionEntity

@Database(
    entities = [GoalEntity::class, SessionEntity::class, CoachMessageEntity::class],
    version = 1,
    exportSchema = true,
)
@TypeConverters(Converters::class)
abstract class OnTrackDatabase : RoomDatabase() {
    abstract fun goalDao(): GoalDao
    abstract fun sessionDao(): SessionDao
    abstract fun coachMessageDao(): CoachMessageDao

    companion object {
        const val NAME = "ontrack.db"
    }
}
