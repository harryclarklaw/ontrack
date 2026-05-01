package com.ontrack.data.model

enum class Category(val display: String) {
    RUNNING("Running"),
    CLIMBING("Climbing"),
    MARTIAL_ARTS("Martial arts"),
    STUDY("Study"),
    READING("Reading"),
    REST("Rest");

    companion object {
        fun from(raw: String): Category =
            entries.firstOrNull { it.name == raw } ?: REST
    }
}
