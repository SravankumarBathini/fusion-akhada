-- Run this migration in the Supabase SQL editor before production use.
alter table public.profiles
    add column if not exists user_id uuid references auth.users(id);

create index if not exists profiles_user_id_idx
    on public.profiles(user_id);

alter table public.profiles enable row level security;

drop policy if exists "Users can read their own profiles"
    on public.profiles;
drop policy if exists "Users can create their own profiles"
    on public.profiles;
drop policy if exists "Users can update their own profiles"
    on public.profiles;
drop policy if exists "Users can delete their own profiles"
    on public.profiles;

create policy "Users can read their own profiles"
    on public.profiles for select
    using (auth.uid() = user_id);

create policy "Users can create their own profiles"
    on public.profiles for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own profiles"
    on public.profiles for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users can delete their own profiles"
    on public.profiles for delete
    using (auth.uid() = user_id);

-- Child tables must be tenant-scoped as well. These policies make the
-- profile ownership relationship the authorization boundary for plans/history.
alter table public.workout_plans enable row level security;
alter table public.workout_history enable row level security;

create index if not exists workout_plans_profile_id_idx
    on public.workout_plans(profile_id);
create index if not exists workout_history_profile_id_idx
    on public.workout_history(profile_id);

drop policy if exists "Users can read their own workout plans"
    on public.workout_plans;
drop policy if exists "Users can create their own workout plans"
    on public.workout_plans;
drop policy if exists "Users can update their own workout plans"
    on public.workout_plans;
drop policy if exists "Users can delete their own workout plans"
    on public.workout_plans;

create policy "Users can read their own workout plans"
    on public.workout_plans for select
    using (exists (
        select 1 from public.profiles
        where profiles.id = workout_plans.profile_id
          and profiles.user_id = auth.uid()
    ));

create policy "Users can create their own workout plans"
    on public.workout_plans for insert
    with check (exists (
        select 1 from public.profiles
        where profiles.id = workout_plans.profile_id
          and profiles.user_id = auth.uid()
    ));

create policy "Users can update their own workout plans"
    on public.workout_plans for update
    using (exists (
        select 1 from public.profiles
        where profiles.id = workout_plans.profile_id
          and profiles.user_id = auth.uid()
    ))
    with check (exists (
        select 1 from public.profiles
        where profiles.id = workout_plans.profile_id
          and profiles.user_id = auth.uid()
    ));

create policy "Users can delete their own workout plans"
    on public.workout_plans for delete
    using (exists (
        select 1 from public.profiles
        where profiles.id = workout_plans.profile_id
          and profiles.user_id = auth.uid()
    ));

drop policy if exists "Users can read their own workout history"
    on public.workout_history;
drop policy if exists "Users can create their own workout history"
    on public.workout_history;
drop policy if exists "Users can update their own workout history"
    on public.workout_history;
drop policy if exists "Users can delete their own workout history"
    on public.workout_history;

create policy "Users can read their own workout history"
    on public.workout_history for select
    using (exists (
        select 1 from public.profiles
        where profiles.id = workout_history.profile_id
          and profiles.user_id = auth.uid()
    ));

create policy "Users can create their own workout history"
    on public.workout_history for insert
    with check (exists (
        select 1 from public.profiles
        where profiles.id = workout_history.profile_id
          and profiles.user_id = auth.uid()
    ));

create policy "Users can update their own workout history"
    on public.workout_history for update
    using (exists (
        select 1 from public.profiles
        where profiles.id = workout_history.profile_id
          and profiles.user_id = auth.uid()
    ))
    with check (exists (
        select 1 from public.profiles
        where profiles.id = workout_history.profile_id
          and profiles.user_id = auth.uid()
    ));

create policy "Users can delete their own workout history"
    on public.workout_history for delete
    using (exists (
        select 1 from public.profiles
        where profiles.id = workout_history.profile_id
          and profiles.user_id = auth.uid()
    ));
