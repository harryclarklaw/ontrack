# Supabase setup

OnTrack stores its plan in Postgres on Supabase. The MCP server (this repo's
`mcp-server/`) reads/writes here, and Phase B will sync the Android app
through the same tables.

## One-time setup

1. Create a project at https://supabase.com (free tier is plenty).
2. SQL Editor → paste `migrations/0001_init.sql` → run.
3. Authentication → Users → "Add user" with email/password (yours).
4. Copy the new user's `id` (UUID). You'll set this as `ONTRACK_USER_ID`
   for the MCP server.
5. Project Settings → API:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` key (treat as a secret) → `SUPABASE_SERVICE_KEY`

That's it. The plan is empty at this point — run `seed_default_plan` from
Claude Code on first chat to populate the 4-week starter plan.

## Schema

| Table | Purpose |
| --- | --- |
| `goals` | Long-term targets (10K time, V-grade, AIGP cert, …) |
| `sessions` | Planned / completed / skipped training & study blocks |
| `coach_messages` | Chat history with the AI coach |

All three are RLS-protected with a single policy: `user_id = auth.uid()`.
The MCP server bypasses RLS via the service-role key but explicitly filters
every query by `user_id`, so it stays scoped to one user.

## Resetting

To wipe the schema during dev:

```sql
drop table if exists public.coach_messages cascade;
drop table if exists public.sessions cascade;
drop table if exists public.goals cascade;
drop function if exists public.ontrack_set_updated_at cascade;
```

then re-run the migration.
