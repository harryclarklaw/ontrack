package com.ontrack.data.model

enum class SessionType(val display: String, val category: Category) {
    EASY_RUN("Easy run", Category.RUNNING),
    TEMPO_RUN("Tempo run", Category.RUNNING),
    LONG_RUN("Long run", Category.RUNNING),
    INTERVAL_RUN("Intervals", Category.RUNNING),
    RECOVERY_RUN("Recovery run", Category.RUNNING),

    BOULDER("Bouldering", Category.CLIMBING),
    LEAD("Lead climbing", Category.CLIMBING),

    MARTIAL_ARTS("Martial arts", Category.MARTIAL_ARTS),

    STUDY_CLAUDE_CODE("Claude Code study", Category.STUDY),
    STUDY_AIGP("AIGP study", Category.STUDY),
    STUDY_GENERAL("Study block", Category.STUDY),

    READING("Professional reading", Category.READING),

    REST("Rest", Category.REST);

    companion object {
        fun from(raw: String): SessionType =
            entries.firstOrNull { it.name == raw } ?: REST
    }
}
