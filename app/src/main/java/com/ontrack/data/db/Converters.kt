package com.ontrack.data.db

import androidx.room.TypeConverter
import kotlinx.datetime.Instant
import kotlinx.datetime.LocalDate
import kotlinx.datetime.LocalTime

class Converters {
    @TypeConverter
    fun localDateToString(d: LocalDate?): String? = d?.toString()

    @TypeConverter
    fun stringToLocalDate(s: String?): LocalDate? = s?.let(LocalDate::parse)

    @TypeConverter
    fun localTimeToString(t: LocalTime?): String? = t?.toString()

    @TypeConverter
    fun stringToLocalTime(s: String?): LocalTime? = s?.let(LocalTime::parse)

    @TypeConverter
    fun instantToEpoch(i: Instant?): Long? = i?.toEpochMilliseconds()

    @TypeConverter
    fun epochToInstant(ms: Long?): Instant? = ms?.let(Instant::fromEpochMilliseconds)
}
