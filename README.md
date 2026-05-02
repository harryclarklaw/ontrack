# OnTrack

A personal-development planner for Android, inspired by Runna. Tracks running,
bouldering, martial arts, study sessions (Claude Code, AIGP), and professional
reading on a single weekly plan, with an AI coach that holistically reviews
progress and reschedules sessions when life gets in the way.

## Features (v0.1 MVP)

- **Weekly plan view** — Mon–Sun layout with the user's actual rhythm seeded:
  martial arts Mon evening, runs Tue/Thu/Sat, climbing Fri/Sun, study weekday
  evenings, Claude Code/AI weekend afternoons, daily professional reading.
- **Today** — quick view of today's sessions; tick off / skip in one tap.
- **Goals** — long-term goals (10K time, V-grade, AIGP cert, Claude Code
  projects) with target dates and metrics.
- **AI coach** — chat-style coach (Claude API) that sees your active goals and
  upcoming plan, can swap sessions, and enforces constraints (no back-to-back
  hard runs, Monday martial arts is fixed, etc.).
- **Strava sync** — OAuth flow + recent-activity import; auto-marks planned
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

To chat to the planner from a laptop (e.g. this Claude Code session), the
plan needs to live somewhere both the phone and the laptop can reach.
Three options, ranked by effort:

1. **MCP server + shared backend (recommended).** Move the source of truth to
   a small backend (Postgres on Supabase / Neon, or Cloudflare D1). The
   Android app reads/writes via REST. A small Node/Python/Kotlin process
   exposes the same operations as a Model Context Protocol server. Add it to
   `~/.claude.json` — Claude Code calls `complete_session`, `swap_sessions`,
   etc. directly. The tool definitions in `CoachTools.kt` map 1:1 to the
   MCP tool list, so most of the work is already done.
2. **On-device HTTP server.** Embed Ktor in the app and bind to local
   network when the app is open. Claude Code on the same wifi hits
   `http://phone-ip:8080/sessions`. No backend, but only works while the
   app is foregrounded and devices are on the same network.
3. **Sync file in cloud storage.** Export plan + goals to a JSON file in
   Drive / iCloud. Both clients edit the file. Simplest but consistency
   becomes a problem with concurrent edits.

Option 1 is the right long-term shape. The backend swap is the first move;
the MCP server is then \~200 lines.

## Roadmap

- **Backend + MCP server** (see above) so the plan is editable from any
  Claude Code session.
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
