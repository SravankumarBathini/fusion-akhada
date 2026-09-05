-- =====================================================================
-- Credit #4 — Single-RPC user snapshot (replaces 3 sequential SELECTs)
-- =====================================================================
-- Deploy this after 001_add_profile_ownership.sql + 002_registration_events.sql
--
-- Postgres composite + JSONB aggregation means application can make ONE
-- Supabase .rpc("get_user_snapshot", {user_id_in: "..."}) call instead of:
--   1. SELECT * FROM profiles         WHERE user_id = ? LIMIT 1
--   2. SELECT * FROM workout_plans   WHERE profile_id = ? LIMIT 1
--   3. SELECT * FROM workout_history WHERE profile_id = ? ORDER BY ...
--
-- Row Level Security from 001_add_profile_ownership.sql continues to apply
-- because the function is SECURITY INVOKER (default) and tables are read
-- directly: the caller (authenticated user) still only sees their own rows.

CREATE OR REPLACE FUNCTION public.get_user_snapshot(user_id_in uuid)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER
AS $$
    WITH
    latest_profile AS (
        SELECT id, profile_data
        FROM public.profiles
        WHERE user_id = user_id_in
        ORDER BY created_at DESC
        LIMIT 1
    ),
    latest_plan AS (
        SELECT plan_data
        FROM public.workout_plans
        WHERE profile_id = (SELECT id FROM latest_profile)
        ORDER BY created_at DESC
        LIMIT 1
    ),
    history_array AS (
        SELECT COALESCE(jsonb_agg(wh.workout_data ORDER BY wh.workout_date ASC, wh.workout_time ASC), '[]'::jsonb) AS workouts
        FROM public.workout_history wh
        WHERE wh.profile_id = (SELECT id FROM latest_profile)
    )
    SELECT to_jsonb(snap)
    FROM (
        SELECT
            (SELECT id           FROM latest_profile)                          AS profile_id,
            (SELECT COALESCE(profile_data, '{}'::jsonb) FROM latest_profile)  AS profile,
            (SELECT plan_data    FROM latest_plan)                             AS workout_plan,
            (SELECT workouts     FROM history_array)                           AS workout_history
    ) snap;
$$;

COMMENT ON FUNCTION public.get_user_snapshot(uuid) IS
'Batched single-RPC loader: returns {profile_id, profile, workout_plan, workout_history} for one Supabase user. Replaces 3 sequential SELECTs on every cache-miss render.';
