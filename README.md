# OnTrack

A personal-development planner inspired by Runna. Tracks running,
bouldering, martial arts, study sessions (Claude Code, AIGP), and
professional reading on a single weekly plan, with an AI coach that
reviews progress holistically and reschedules sessions when life gets
in the way.

The repo contains three components:

- **`app/`** — Android client (Kotlin + Jetpack Compose).
- **`supabase/`** — SQL schema for the shared backend.
- **`mcp-server/`** — Model Context Protocol server so you can drive the
  plan from Claude Code (or any MCP client) via natural-language chat.

## Features (v0.2)

- **Weekly plan view** — Mon–Sun layout with the user's actual rhythm
  seeded: martial arts Mon evening, runs Tue/Thu/Sat, climbing Fri/Sun,
  study weekday evenings, Claude Code/AI weekend afternoons, daily
  professional reading.
- **Today** — today's sessions; tick off / skip in one tap.
- **Goals** — long-term goals (10K time, V-grade, AIGP cert, Claude Code
  projects) with target dates and metrics.
- **In-app AI coach (tool-driven)** — chat that *acts*. Anthropic Messages
  API with a tool-call loop: model calls `get_plan`, `swap_sessions`,
  `reschedule_session`, etc. and the app applies edits to Room directly.
- **MCP server** — same set of tools, exposed over stdio. Wire it into
  Claude Code and update the plan from your laptop.
- **Strava sync** — OAuth + recent-activity import; auto-marks planned
  runs complete and stores actual distance/pace/HR.

## Stack

- Kotlin + Jetpack Compose (Material 3, dark theme)
- Room (SQLite) for the plan, goals, and coach history
- Hilt for DI
- Retrofit + kotlinx.serialization for Anthropic + Strava
- DataStore for OAuth tokens
- kotlinx.datetime for plan/date math
- Android min SDK 26, target 35

## Project layout

```
app/src/main/java/com/ontrack/
├── OnTrackApp.kt              # @HiltAndroidApp, seeds data on first launch
├── MainActivity.kt            # hosts Compose nav + Strava OAuth callback
├── data/
│   ├── model/                 # domain types (Goal, Session, enums)
│   ├── db/                    # Room entities, DAOs, database, converters
│   ├── repository/            # repos used by view models
│   └── seed/                  # 4-week default plan generator
├── di/                        # Hilt modules (database, network)
├── integrations/
│   ├── strava/                # OAuth (StravaAuth), API, sync logic
│   └── ai/                    # Anthropic API, CoachService
├── ui/
│   ├── theme/                 # Material 3 dark theme + category colours
│   ├── nav/                   # bottom-nav scaffold
│   ├── components/            # SessionCard, etc.
│   ├── today/  plan/  goals/  coach/   # screens + view models
└── util/Dates.kt
```

## Setup

1. Open the project in Android Studio (Hedgehog/Iguana or newer; AGP 8.7.x).
2. `cp local.properties.example local.properties` and fill in:
   - `sdk.dir` — path to the Android SDK on your machine.
   - `ANTHROPIC_API_KEY` — optional; without it the coach replies in offline
     stub mode.
   - `STRAVA_CLIENT_ID` / `STRAVA_CLIENT_SECRET` — create a Strava API
     application at https://www.strava.com/settings/api and set the
     "Authorization Callback Domain" to `strava` (matching `ontrack://strava`).
3. Sync Gradle. First launch seeds 4 weeks of the default plan + 4 goals.

## In-app coach (tool-driven)

The coach uses Anthropic tool-calls to read and edit the plan directly. Every
chat turn runs an agentic loop: model proposes tools, app executes them
against Room, results feed back, model writes the final summary.

Available tools (see `integrations/ai/CoachTools.kt`):

| Tool | What it does |
| --- | --- |
| `get_plan(week_offset?)` | Reads sessions for current/relative week |
| `get_goals` | Reads active goals |
| `complete_session(id)` | Mark done |
| `skip_session(id)` | Mark skipped |
| `reschedule_session(id, new_date)` | Move to a different date |
| `swap_sessions(a, b)` | Swap two sessions |
| `add_session(date, type, title, duration, ...)` | Add new session |
| `delete_session(id)` | Remove |
| `update_session_notes(id, notes)` | Edit notes |

Example prompts:

- "I'm wrecked, swap Thursday's tempo for an easy run."
- "Move tomorrow's reading to the weekend."
- "I missed the long run yesterday — push it to Sunday and shorten it."

The model is instructed to `get_plan` first to look up real session ids
before mutating, and to keep Monday martial arts fixed.

## Driving the plan from Claude Code

The MCP server in `mcp-server/` exposes the same tool set as the in-app
coach over stdio. Wire it into your Claude Code config and you can chat
your plan into shape from your laptop:

> Seed my OnTrack default plan.
> Show me this week.
> I'm wrecked — swap Thursday's tempo for an easy run.

Setup is two steps: run the SQL in `supabase/migrations/0001_init.sql`
against a fresh Supabase project, then `npm install && npm run build` in
`mcp-server/` and add the entry to `~/.claude.json`. Full instructions in
`mcp-server/README.md` and `supabase/README.md`.

The MCP tool list mirrors the Android `CoachTools.kt` 1:1, so the in-app
coach and Claude Code edits the same shape of data.

### Phase B (next): Android ↔ Supabase sync

This commit lands the backend + MCP server. Phase B will switch the
Android client from local-Room-only to remote-first against Supabase, so
edits made via Claude Code show up on the phone (and vice versa). Plan:

- Authenticate the app against Supabase (email/password to start)
- Push local mutations to Supabase as they happen
- Pull on app open and on a manual sync, merging by id
- Keep Room as the offline cache

Until Phase B lands, the Android app continues to use its local Room
database; MCP-driven changes live in Supabase only.

## Roadmap

- **Phase B Android sync** (see above).
- **Drag-and-drop swap** between days in the Plan view.
- **Goal-driven plan generation** — target race / cert date drives weekly
  progression (run mileage build, climbing project cycles, AIGP modules).
- **Heart-rate / RPE tracking** post-session.
- **Runna plan import** — Runna has no public API; planned approach is OCR /
  paste of weekly plan, parsed into structured workouts.
- **Notifications** — morning brief, evening logging nudge.
- **Widgets** — today's next session on the home screen.

## Notes on integrations

- **Strava**: OAuth uses Chrome Custom Tabs; tokens are persisted via
  DataStore and refreshed on demand. `StravaSync` matches activities to
  planned runs by date proximity (±1 day) — good enough for a solo user.
- **Claude / Anthropic**: `CoachService` builds a system prompt with the
  active plan + goals as context and calls the Messages API directly. For a
  multi-user version this should move behind a backend proxy so the API key
  is not shipped in the APK.
