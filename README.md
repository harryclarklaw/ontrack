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

## Roadmap

- **Drag-and-drop swap** between days.
- **Coach tool-calls** — let the coach apply session edits directly, not just
  suggest them in chat.
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
