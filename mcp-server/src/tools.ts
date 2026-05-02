import type { Tool } from "@modelcontextprotocol/sdk/types.js";
import { supabase, USER_ID } from "./supabase.js";
import { seedDefaultPlan } from "./seed.js";

export const tools: Tool[] = [
    {
        name: "get_plan",
        description:
            "Returns sessions for a week, ordered by date and time. Defaults to the current week. " +
            "Pass week_offset (0=this week, 1=next, -1=last).",
        inputSchema: {
            type: "object",
            properties: {
                week_offset: {
                    type: "integer",
                    description: "Week offset from this week. Defaults to 0.",
                },
            },
        },
    },
    {
        name: "get_today",
        description: "Returns today's sessions ordered by start_time.",
        inputSchema: { type: "object", properties: {} },
    },
    {
        name: "get_goals",
        description: "Returns all of the user's goals (active first, then by target date).",
        inputSchema: { type: "object", properties: {} },
    },
    {
        name: "complete_session",
        description: "Marks a session as completed.",
        inputSchema: {
            type: "object",
            properties: { session_id: { type: "string", description: "Session UUID" } },
            required: ["session_id"],
        },
    },
    {
        name: "skip_session",
        description: "Marks a session as skipped (intentionally not done).",
        inputSchema: {
            type: "object",
            properties: { session_id: { type: "string" } },
            required: ["session_id"],
        },
    },
    {
        name: "reschedule_session",
        description: "Moves a session to a new date (YYYY-MM-DD). Time of day is preserved.",
        inputSchema: {
            type: "object",
            properties: {
                session_id: { type: "string" },
                new_date: { type: "string", description: "ISO date YYYY-MM-DD" },
            },
            required: ["session_id", "new_date"],
        },
    },
    {
        name: "swap_sessions",
        description:
            "Swaps the dates and start times of two sessions. Use when the user wants to trade " +
            "two existing sessions (e.g. \"swap Thursday's tempo with Saturday's long run\").",
        inputSchema: {
            type: "object",
            properties: {
                session_a_id: { type: "string" },
                session_b_id: { type: "string" },
            },
            required: ["session_a_id", "session_b_id"],
        },
    },
    {
        name: "add_session",
        description:
            "Adds a new session. type must be one of: EASY_RUN, TEMPO_RUN, LONG_RUN, " +
            "INTERVAL_RUN, RECOVERY_RUN, BOULDER, LEAD, MARTIAL_ARTS, STUDY_CLAUDE_CODE, " +
            "STUDY_AIGP, STUDY_GENERAL, READING, REST.",
        inputSchema: {
            type: "object",
            properties: {
                date: { type: "string", description: "YYYY-MM-DD" },
                type: { type: "string" },
                title: { type: "string" },
                duration_minutes: { type: "integer", minimum: 0 },
                start_time: { type: "string", description: "Optional HH:MM (24h)" },
                notes: { type: "string", description: "Optional" },
                goal_id: { type: "string", description: "Optional goal UUID" },
                planned_metrics: {
                    type: "object",
                    description:
                        "Optional structured planned metrics, e.g. " +
                        "{distance_km: 10, target_pace: \"5:00/km\"}.",
                },
            },
            required: ["date", "type", "title", "duration_minutes"],
        },
    },
    {
        name: "delete_session",
        description: "Removes a session by id.",
        inputSchema: {
            type: "object",
            properties: { session_id: { type: "string" } },
            required: ["session_id"],
        },
    },
    {
        name: "update_session_notes",
        description: "Replaces the notes field on a session (e.g. workout breakdown, RPE).",
        inputSchema: {
            type: "object",
            properties: {
                session_id: { type: "string" },
                notes: { type: "string" },
            },
            required: ["session_id", "notes"],
        },
    },
    {
        name: "update_goal_progress",
        description: "Updates the current_value of a goal (e.g. \"V5\", \"45:32\").",
        inputSchema: {
            type: "object",
            properties: {
                goal_id: { type: "string" },
                current_value: { type: "string" },
            },
            required: ["goal_id", "current_value"],
        },
    },
    {
        name: "seed_default_plan",
        description:
            "First-run helper. If the user has no sessions, generates the 4-week starter plan " +
            "and 4 goals matching their stated rhythm: Mon martial arts, Tue/Thu/Sat runs, " +
            "Fri/Sun climbing, weekday-evening study, weekend Claude Code/AIGP, daily reading. " +
            "Returns 'already seeded' if data exists.",
        inputSchema: { type: "object", properties: {} },
    },
];

export async function callTool(
    name: string,
    args: Record<string, unknown>,
): Promise<unknown> {
    switch (name) {
        case "get_plan":
            return getPlan(numArg(args, "week_offset", 0));
        case "get_today":
            return getToday();
        case "get_goals":
            return getGoals();
        case "complete_session":
            return setStatus(strArg(args, "session_id"), "COMPLETED");
        case "skip_session":
            return setStatus(strArg(args, "session_id"), "SKIPPED");
        case "reschedule_session":
            return reschedule(strArg(args, "session_id"), strArg(args, "new_date"));
        case "swap_sessions":
            return swapSessions(strArg(args, "session_a_id"), strArg(args, "session_b_id"));
        case "add_session":
            return addSession(args);
        case "delete_session":
            return deleteSession(strArg(args, "session_id"));
        case "update_session_notes":
            return updateNotes(strArg(args, "session_id"), strArg(args, "notes"));
        case "update_goal_progress":
            return updateGoalProgress(strArg(args, "goal_id"), strArg(args, "current_value"));
        case "seed_default_plan":
            return seedDefaultPlan();
        default:
            throw new Error(`Unknown tool: ${name}`);
    }
}

// ---------- arg helpers ----------

function strArg(args: Record<string, unknown>, key: string): string {
    const v = args[key];
    if (typeof v !== "string" || v.length === 0) {
        throw new Error(`Missing string arg '${key}'`);
    }
    return v;
}

function numArg(args: Record<string, unknown>, key: string, fallback?: number): number {
    const v = args[key];
    if (v === undefined || v === null) {
        if (fallback !== undefined) return fallback;
        throw new Error(`Missing number arg '${key}'`);
    }
    const n = typeof v === "number" ? v : Number(v);
    if (Number.isNaN(n)) throw new Error(`Invalid number for '${key}'`);
    return n;
}

function optionalStr(args: Record<string, unknown>, key: string): string | null {
    const v = args[key];
    return typeof v === "string" && v.length > 0 ? v : null;
}

// ---------- date helpers ----------

function startOfWeek(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay() === 0 ? 7 : d.getDay();
    d.setDate(d.getDate() - (day - 1));
    d.setHours(0, 0, 0, 0);
    return d;
}

function isoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
}

// ---------- queries ----------

async function getPlan(weekOffset: number) {
    const start = startOfWeek(new Date());
    start.setDate(start.getDate() + weekOffset * 7);
    const end = new Date(start);
    end.setDate(end.getDate() + 7);
    const { data, error } = await supabase
        .from("sessions")
        .select("*")
        .eq("user_id", USER_ID)
        .gte("date", isoDate(start))
        .lt("date", isoDate(end))
        .order("date", { ascending: true })
        .order("start_time", { ascending: true, nullsFirst: false });
    if (error) throw error;
    return { week_start: isoDate(start), sessions: data };
}

async function getToday() {
    const today = isoDate(new Date());
    const { data, error } = await supabase
        .from("sessions")
        .select("*")
        .eq("user_id", USER_ID)
        .eq("date", today)
        .order("start_time", { ascending: true, nullsFirst: false });
    if (error) throw error;
    return { date: today, sessions: data };
}

async function getGoals() {
    const { data, error } = await supabase
        .from("goals")
        .select("*")
        .eq("user_id", USER_ID)
        .order("active", { ascending: false })
        .order("target_date", { ascending: true });
    if (error) throw error;
    return data;
}

async function setStatus(id: string, status: string) {
    const { data, error } = await supabase
        .from("sessions")
        .update({ status })
        .eq("id", id)
        .eq("user_id", USER_ID)
        .select()
        .single();
    if (error) throw error;
    return { ok: true, session: data };
}

async function reschedule(id: string, newDate: string) {
    const { data, error } = await supabase
        .from("sessions")
        .update({ date: newDate })
        .eq("id", id)
        .eq("user_id", USER_ID)
        .select()
        .single();
    if (error) throw error;
    return { ok: true, session: data };
}

async function swapSessions(a: string, b: string) {
    const { data: rows, error } = await supabase
        .from("sessions")
        .select("id, date, start_time")
        .in("id", [a, b])
        .eq("user_id", USER_ID);
    if (error) throw error;
    if (!rows || rows.length !== 2) {
        throw new Error(`Expected 2 sessions, got ${rows?.length ?? 0}`);
    }
    const sa = rows.find((r) => r.id === a);
    const sb = rows.find((r) => r.id === b);
    if (!sa || !sb) throw new Error("Could not match both session ids");

    const { error: updAErr } = await supabase
        .from("sessions")
        .update({ date: sb.date, start_time: sb.start_time })
        .eq("id", a)
        .eq("user_id", USER_ID);
    if (updAErr) throw updAErr;

    const { error: updBErr } = await supabase
        .from("sessions")
        .update({ date: sa.date, start_time: sa.start_time })
        .eq("id", b)
        .eq("user_id", USER_ID);
    if (updBErr) throw updBErr;

    return {
        ok: true,
        a: { id: a, new_date: sb.date, new_start_time: sb.start_time },
        b: { id: b, new_date: sa.date, new_start_time: sa.start_time },
    };
}

async function addSession(args: Record<string, unknown>) {
    const startTimeRaw = optionalStr(args, "start_time");
    const startTime = startTimeRaw === null
        ? null
        : startTimeRaw.length === 5
            ? `${startTimeRaw}:00`
            : startTimeRaw;
    const session = {
        user_id: USER_ID,
        date: strArg(args, "date"),
        type: strArg(args, "type"),
        title: strArg(args, "title"),
        duration_minutes: numArg(args, "duration_minutes"),
        start_time: startTime,
        notes: optionalStr(args, "notes") ?? "",
        goal_id: optionalStr(args, "goal_id"),
        planned_metrics:
            args.planned_metrics && typeof args.planned_metrics === "object"
                ? args.planned_metrics
                : {},
    };
    const { data, error } = await supabase
        .from("sessions")
        .insert(session)
        .select()
        .single();
    if (error) throw error;
    return { ok: true, session: data };
}

async function deleteSession(id: string) {
    const { error } = await supabase
        .from("sessions")
        .delete()
        .eq("id", id)
        .eq("user_id", USER_ID);
    if (error) throw error;
    return { ok: true, id };
}

async function updateNotes(id: string, notes: string) {
    const { data, error } = await supabase
        .from("sessions")
        .update({ notes })
        .eq("id", id)
        .eq("user_id", USER_ID)
        .select()
        .single();
    if (error) throw error;
    return { ok: true, session: data };
}

async function updateGoalProgress(id: string, currentValue: string) {
    const { data, error } = await supabase
        .from("goals")
        .update({ current_value: currentValue })
        .eq("id", id)
        .eq("user_id", USER_ID)
        .select()
        .single();
    if (error) throw error;
    return { ok: true, goal: data };
}
