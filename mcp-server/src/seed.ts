import { supabase, USER_ID } from "./supabase.js";

function startOfWeek(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay() === 0 ? 7 : d.getDay();
    d.setDate(d.getDate() - (day - 1));
    d.setHours(0, 0, 0, 0);
    return d;
}

function addDays(d: Date, n: number): Date {
    const r = new Date(d);
    r.setDate(r.getDate() + n);
    return r;
}

function addMonths(d: Date, n: number): Date {
    const r = new Date(d);
    r.setMonth(r.getMonth() + n);
    return r;
}

function isoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
}

interface GoalIds {
    tenK: string;
    v6: string;
    aigp: string;
    claude: string;
}

/**
 * Mirrors the Android SeedData class. Generates 4 weeks of sessions matching
 * the user's stated rhythm: Monday martial arts, Tue/Thu/Sat runs,
 * Fri/Sun climbing, weekday-evening study, weekend Claude Code/AIGP, daily
 * professional reading (skipping Monday — martial-arts night).
 */
export async function seedDefaultPlan(): Promise<unknown> {
    const { count, error: countErr } = await supabase
        .from("sessions")
        .select("*", { count: "exact", head: true })
        .eq("user_id", USER_ID);
    if (countErr) throw countErr;
    if ((count ?? 0) > 0) {
        return { ok: false, message: "Plan already seeded — has " + count + " sessions" };
    }

    const today = new Date();
    const goalsInsert = [
        {
            user_id: USER_ID,
            title: "10K under 45 minutes",
            description: "Build aerobic base, add tempo + intervals.",
            category: "RUNNING",
            target_date: isoDate(addMonths(today, 3)),
            metric: "10K time",
            target_value: "45:00",
            current_value: "—",
        },
        {
            user_id: USER_ID,
            title: "Send V6 outdoors",
            description: "Strength + technique sessions, project a route.",
            category: "CLIMBING",
            target_date: isoDate(addMonths(today, 6)),
            metric: "Hardest send",
            target_value: "V6",
            current_value: "V4",
        },
        {
            user_id: USER_ID,
            title: "Pass AIGP certification",
            description: "Study modules + practice tests.",
            category: "STUDY",
            target_date: isoDate(addMonths(today, 4)),
            metric: "Status",
            target_value: "Certified",
            current_value: "In progress",
        },
        {
            user_id: USER_ID,
            title: "Ship 3 Claude Code projects",
            description: "Build, document, and share.",
            category: "STUDY",
            target_date: isoDate(addMonths(today, 6)),
            metric: "Projects shipped",
            target_value: "3",
            current_value: "0",
        },
    ];

    const { data: goalsRows, error: goalsErr } = await supabase
        .from("goals")
        .insert(goalsInsert)
        .select();
    if (goalsErr) throw goalsErr;
    if (!goalsRows || goalsRows.length !== 4) {
        throw new Error("Goals insert returned unexpected row count");
    }

    const findGoal = (prefix: string): string => {
        const g = goalsRows.find((row: { title: string }) => row.title.startsWith(prefix));
        if (!g) throw new Error("Missing seeded goal: " + prefix);
        return g.id as string;
    };

    const ids: GoalIds = {
        tenK: findGoal("10K"),
        v6: findGoal("Send V6"),
        aigp: findGoal("Pass AIGP"),
        claude: findGoal("Ship 3"),
    };

    const weekStart = startOfWeek(today);
    const sessions: Record<string, unknown>[] = [];
    for (let w = 0; w < 4; w++) {
        sessions.push(...weekTemplate(addDays(weekStart, w * 7), w, ids));
    }

    const { error: sessionsErr } = await supabase.from("sessions").insert(sessions);
    if (sessionsErr) throw sessionsErr;

    return { ok: true, goals: goalsRows.length, sessions: sessions.length };
}

function weekTemplate(weekStart: Date, weekIndex: number, g: GoalIds): Record<string, unknown>[] {
    const out: Record<string, unknown>[] = [];
    const day = (offset: number) => isoDate(addDays(weekStart, offset));

    out.push({
        user_id: USER_ID,
        date: day(0),
        start_time: "19:00:00",
        duration_minutes: 90,
        type: "MARTIAL_ARTS",
        title: "Martial arts class",
        notes: "Recurring Monday class.",
    });

    out.push({
        user_id: USER_ID,
        date: day(1),
        start_time: "07:00:00",
        duration_minutes: 45,
        type: "EASY_RUN",
        title: "Easy 6km",
        goal_id: g.tenK,
        planned_metrics: { distance_km: 6, target_pace: "easy", rpe: 4 },
    });
    out.push({
        user_id: USER_ID,
        date: day(1),
        start_time: "20:00:00",
        duration_minutes: 60,
        type: "STUDY_AIGP",
        title: "AIGP module",
        goal_id: g.aigp,
    });

    out.push({
        user_id: USER_ID,
        date: day(2),
        start_time: "20:00:00",
        duration_minutes: 60,
        type: "STUDY_GENERAL",
        title: "Study block",
        goal_id: g.aigp,
    });

    const tempoMin = 50 + weekIndex * 5;
    const tempoKm = 4 + weekIndex;
    out.push({
        user_id: USER_ID,
        date: day(3),
        start_time: "07:00:00",
        duration_minutes: tempoMin,
        type: "TEMPO_RUN",
        title: `Tempo ${tempoKm}km @ threshold`,
        goal_id: g.tenK,
        planned_metrics: { warmup_km: 2, tempo_km: tempoKm, cooldown_km: 1.5 },
    });
    out.push({
        user_id: USER_ID,
        date: day(3),
        start_time: "20:00:00",
        duration_minutes: 60,
        type: "STUDY_AIGP",
        title: "AIGP practice questions",
        goal_id: g.aigp,
    });

    out.push({
        user_id: USER_ID,
        date: day(4),
        start_time: "18:30:00",
        duration_minutes: 90,
        type: "BOULDER",
        title: "Bouldering session",
        goal_id: g.v6,
        planned_metrics: { target_grade: "V4-V5", focus: "power" },
    });

    const longKm = 10 + weekIndex * 2;
    out.push({
        user_id: USER_ID,
        date: day(5),
        start_time: "08:30:00",
        duration_minutes: 70 + weekIndex * 10,
        type: "LONG_RUN",
        title: `Long run ${longKm}km`,
        goal_id: g.tenK,
        planned_metrics: { distance_km: longKm, target_pace: "easy" },
    });
    out.push({
        user_id: USER_ID,
        date: day(5),
        start_time: "14:00:00",
        duration_minutes: 120,
        type: "STUDY_CLAUDE_CODE",
        title: "Claude Code project work",
        goal_id: g.claude,
    });

    out.push({
        user_id: USER_ID,
        date: day(6),
        start_time: "10:00:00",
        duration_minutes: 90,
        type: "BOULDER",
        title: "Bouldering session",
        goal_id: g.v6,
        planned_metrics: { target_grade: "V4-V5", focus: "endurance" },
    });
    out.push({
        user_id: USER_ID,
        date: day(6),
        start_time: "14:00:00",
        duration_minutes: 120,
        type: "STUDY_CLAUDE_CODE",
        title: "Claude Code project work",
        goal_id: g.claude,
    });

    for (let d = 1; d < 7; d++) {
        out.push({
            user_id: USER_ID,
            date: day(d),
            start_time: "12:30:00",
            duration_minutes: 30,
            type: "READING",
            title: "Professional reading",
        });
    }

    return out;
}
