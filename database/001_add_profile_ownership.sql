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
