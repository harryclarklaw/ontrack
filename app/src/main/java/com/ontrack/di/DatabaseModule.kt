package com.ontrack.di

import android.content.Context
import androidx.room.Room
import com.ontrack.data.db.OnTrackDatabase
import com.ontrack.data.db.dao.CoachMessageDao
import com.ontrack.data.db.dao.GoalDao
import com.ontrack.data.db.dao.SessionDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): OnTrackDatabase =
        Room.databaseBuilder(context, OnTrackDatabase::class.java, OnTrackDatabase.NAME)
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun provideGoalDao(db: OnTrackDatabase): GoalDao = db.goalDao()
    @Provides fun provideSessionDao(db: OnTrackDatabase): SessionDao = db.sessionDao()
    @Provides fun provideCoachMessageDao(db: OnTrackDatabase): CoachMessageDao = db.coachMessageDao()
}
