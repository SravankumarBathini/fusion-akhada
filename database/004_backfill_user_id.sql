-- =====================================================================
-- Credit #4 follow-on — backfill ``profiles.user_id`` for schema-A rows
-- =====================================================================
--
-- WHY THIS EXISTS
-- ---------------
-- After Phase 0 added ``profiles.user_id`` and RLS policies (see
-- 001_add_profile_ownership.sql), 46 of 48 real tenant rows were never
-- backfilled — they retain ``profiles.user_id IS NULL``.
--
-- Those 46 NULL rows still own 100% of the historical workout_plans +
-- workout_history because every pre-Credit-#4 save stored ``profile_id``
-- FK correctly on plan/history but didn't stamp ``profiles.user_id`` on
-- the profile header.  Credit #4's 1-RPC fast path queries
-- ``WHERE profiles.user_id = $1`` — which matches ZERO rows for all 46
-- legacy tenants.  Result: UI renders "0 workouts / 0 plans" and the
-- user thinks they lost their data.
--
-- The Python side (``_load_all_user_data_fallback_legacy`` in storage.py)
-- has a short-term heuristic that finds the "richest" profile_id and
-- loads its plan + history.  That works for single-tenant personal
-- installs BUT IT DEFEATS TENANT ISOLATION ON MULTI-TENANT DEPLOYS.
--
-- Run this migration to close the gap permanently:
--
--     * every NULL ``profiles.user_id`` gets stamped with the
--       authenticated supabase user's auth.uid() who is currently
--       viewing the app (the "current" tenant), OR with an explicit
--       ``:target_user_id`` placeholder you can substitute manually
--       in the SQL editor.
--
--     * RLS policies then work as intended, and Credit #4's 1-RPC fast
--       path in ``get_user_snapshot(user_id_in uuid)`` matches rows
--       directly, no heuristic needed.
--
-- RUNNING IN SUPABASE SQL EDITOR
-- ------------------------------
-- If you're the only tenant (personal app), leave the commented block
-- that uses ``auth.uid()`` and just click "Run".  The profile rows that
-- have ``user_id IS NULL`` get stamped with YOUR current auth.uid().
--
-- If you know the specific user UUID you want to associate, edit the
-- placeholder at the top and then run.

-- start transaction
BEGIN;

-- Option 1 — single-tenant (personal workout trainer):
-- stamp any NULL user_id with the currently-authenticated user's UUID.
-- Uncomment these two lines and skip Option 2:
--
--     UPDATE public.profiles
--        SET user_id     = auth.uid(),
--            updated_at  = COALESCE(updated_at, created_at, now())
--      WHERE user_id IS NULL;

-- Option 2 — explicit target UUID (preferred when you know it):
-- Replace the UUID string below with the real ``auth.users.id`` that
-- should own these rows (find it in Supabase → Authentication → Users):
--
--     DO $$
--     DECLARE
--       target_user_id uuid := '00000000-0000-0000-0000-000000000000';
--     BEGIN
--       UPDATE public.profiles
--          SET user_id     = target_user_id,
--              updated_at  = COALESCE(updated_at, created_at, now())
--        WHERE user_id IS NULL;
--     END $$;

COMMENT ON FUNCTION public.get_user_snapshot(uuid) IS
'Batched single-RPC loader: returns {profile_id, profile, workout_plan, workout_history} for one Supabase user. Replaces 3 sequential SELECTs on every cache-miss render. After 004_backfill_user_id.sql is applied this function hits ALL rows (schema A + schema B) via direct profiles.user_id lookup — no Python-side legacy heuristic needed.';

COMMIT;
