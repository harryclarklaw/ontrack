-- OnTrack initial schema.
-- Run this once in your Supabase project (SQL Editor → paste → run).

create extension if not exists pgcrypto;

-- Goals --------------------------------------------------------------------

create table if not exists public.goals (
    id              uuid primary key default gen_random_uuid(),
    user_id         uuid not null references auth.users(id) on delete cascade,
    title           text not null,
    description     text not null default '',
    category        text not null check (category in (
                        'RUNNING','CLIMBING','MARTIAL_ARTS','STUDY','READING','REST'
                    )),
    target_date     date not null,
    metric          text not null,
    target_value    text not null,
    current_value   text not null default '',
    active          boolean not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists goals_user_idx on public.goals(user_id);

-- Sessions -----------------------------------------------------------------

create table if not exists public.sessions (
    id                  uuid primary key default gen_random_uuid(),
    user_id             uuid not null references auth.users(id) on delete cascade,
    date                date not null,
    start_time          time,
    duration_minutes    int  not null check (duration_minutes >= 0),
    type                text not null,
    title               text not null,
    notes               text not null default '',
    status              text not null default 'PLANNED' check (status in (
                            'PLANNED','COMPLETED','SKIPPED','MISSED'
                        )),
    goal_id             uuid references public.goals(id) on delete set null,
    planned_metrics     jsonb not null default '{}'::jsonb,
    actual_metrics      jsonb not null default '{}'::jsonb,
    strava_activity_id  bigint,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create index if not exists sessions_user_date_idx on public.sessions(user_id, date);
create index if not exists sessions_goal_idx on public.sessions(goal_id);

-- Coach messages -----------------------------------------------------------

create table if not exists public.coach_messages (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references auth.users(id) on delete cascade,
    role        text not null check (role in ('USER','ASSISTANT','SYSTEM')),
    content     text not null,
    created_at  timestamptz not null default now()
);

create index if not exists coach_messages_user_idx
    on public.coach_messages(user_id, created_at);

-- updated_at trigger -------------------------------------------------------

create or replace function public.ontrack_set_updated_at() returns trigger
language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists goals_set_updated_at on public.goals;
create trigger goals_set_updated_at before update on public.goals
    for each row execute function public.ontrack_set_updated_at();

drop trigger if exists sessions_set_updated_at on public.sessions;
create trigger sessions_set_updated_at before update on public.sessions
    for each row execute function public.ontrack_set_updated_at();

-- Row-level security -------------------------------------------------------

alter table public.goals          enable row level security;
alter table public.sessions       enable row level security;
alter table public.coach_messages enable row level security;

drop policy if exists goals_owner          on public.goals;
drop policy if exists sessions_owner       on public.sessions;
drop policy if exists coach_messages_owner on public.coach_messages;

create policy goals_owner on public.goals
    for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy sessions_owner on public.sessions
    for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy coach_messages_owner on public.coach_messages
    for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- Note: the MCP server uses the service-role key, which bypasses RLS but
-- explicitly filters every query by user_id. The Android app (Phase B) will
-- authenticate as a normal user and rely on these policies.
