package com.ontrack.data.model

enum class SessionStatus(val display: String) {
    PLANNED("Planned"),
    COMPLETED("Completed"),
    SKIPPED("Skipped"),
    MISSED("Missed");

    companion object {
        fun from(raw: String): SessionStatus =
            entries.firstOrNull { it.name == raw } ?: PLANNED
    }
}
