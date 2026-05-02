# OnTrack MCP server

A Model Context Protocol server that exposes the OnTrack planner as tools.
Wire it into Claude Code (or any MCP client) and you can update your weekly
plan, log sessions, and tweak goals via natural-language chat.

## Setup

1. Run the Supabase migration in `../supabase/` and create your user
   (see `../supabase/README.md`).

2. Configure env:

   ```sh
   cp .env.example .env
   # fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, ONTRACK_USER_ID
   ```

3. Install + build:

   ```sh
   npm install
   npm run build
   ```

4. Optional — sanity-check it boots without crashing:

   ```sh
   set -a; source .env; set +a
   npm start    # Ctrl-C to exit; should print nothing on stdout
   ```

## Wire to Claude Code

Add to `~/.claude.json` (global) or a project-local `.mcp.json` under
`mcpServers`:

```json
{
  "mcpServers": {
    "ontrack": {
      "command": "node",
      "args": ["/absolute/path/to/ontrack/mcp-server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "https://xxxxx.supabase.co",
        "SUPABASE_SERVICE_KEY": "eyJ...",
        "ONTRACK_USER_ID": "your-uuid"
      }
    }
  }
}
```

Restart Claude Code and run `/mcp` to verify the server is connected.

## First chat

In a Claude Code session:

> Seed my OnTrack default plan.

Then try:

> Show me this week.
> I'm wrecked — swap Thursday's tempo for an easy run.
> Move tomorrow's reading to Saturday afternoon.
> I missed yesterday's long run. Push it to Sunday and shorten it to 12k.

The server will surface session UUIDs as needed; the model will look them up
via `get_plan` first before mutating.

## Tools

| Tool | Purpose |
| --- | --- |
| `get_plan(week_offset?)` | Sessions for a week (0 = this week) |
| `get_today` | Today's sessions |
| `get_goals` | All goals (active first) |
| `complete_session(id)` | Mark done |
| `skip_session(id)` | Mark skipped |
| `reschedule_session(id, new_date)` | Move to new date (time preserved) |
| `swap_sessions(a_id, b_id)` | Trade two sessions' dates/times |
| `add_session(...)` | Insert new session |
| `delete_session(id)` | Remove |
| `update_session_notes(id, notes)` | Edit notes |
| `update_goal_progress(id, current_value)` | Bump goal progress |
| `seed_default_plan` | One-shot 4-week starter (no-op if data exists) |

## Security notes

- The service-role key bypasses RLS. Keep it on your laptop only — it must
  not ship to the Android app.
- The MCP server explicitly filters every query by `user_id` so it stays
  scoped to one human even with the bypass.
- For multi-user, replace the service-role key with the anon key + a real
  auth flow.
