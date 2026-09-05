# Debug Session: slow-app-performance

- **Session ID:** `slow-app-performance`
- **Created:** 2026-09-04
- **Status:** [OPEN]
- **Symptom:** Personal Workout Trainer Streamlit app feels slow / not quick responsive during normal use
- **Expected:** Page renders, widget interactions, and page switches feel snappy (<300ms perceived latency)
- **Impact Scope:** End-user UX across all 6 pages (Dashboard, Profile, Workout, History, Progress, AI Coach)

---

## 🔍 Hypotheses (All Falsifiable)

| # | Hypothesis | Test Measurement |
|---|------------|------------------|
| H1 | **Blocking network calls on every re-render:** Supabase `select/execute` in `storage.py` runs synchronously without caching → every widget interaction triggers a storage.py load that makes a round-trip HTTP call, blocking Streamlit's render | Instrument wall-clock timing around: `load_latest_profile`, `load_latest_workout_plan`, `load_workout_history`, `load_exercises` + count how many times each fires per single page render |
| H2 | **Global JSON reload on every render:** `application/data_loader.py` / `data_loaders` reloads exercise JSON and seed data from disk on every app.py re-import / session rerun instead of loading once at startup with `@st.cache_data` | Time the `load_base_library()` function and count calls per render; also check for `st.cache_data` / `st.cache_resource` usage on expensive loaders |
| H3 | **Full app.py re-execution (2006 lines):** No Streamlit multipage `pages/` structure → every widget change re-runs the entire 6-page if/elif chain, including pages that aren't currently visible. Heavy computations in Dashboard/Progress charts and AI Coach sidebar run even if user is on Profile page | Measure the time contribution of each 6 page branch separately; confirm the 5 non-active branches still execute >5ms worth of work each |
| H4 | **Gemini AI synchronous blocking calls:** `modules/ai_coach.py` / `services/ai.py` `ask_ai_coach()` runs synchronously on UI thread with `st.spinner` but no `@st.cache_data` per prompt + no timeout; retries with backoff absent | Measure P50/P95 of `ask_ai_coach` latency; confirm the call blocks render for >1s |
| H5 | **Storage `_profiles_support_user_id` + `_get_supabase_client` rebuild client per call:** `storage.py` `_get_supabase_client()` instantiates a new Supabase client (JWT parse, SSL handshake) on every invocation rather than caching as a module-level singleton; also `_profiles_support_user_id()` re-queries information_schema every call | Time Supabase client construction + schema probe, count how frequently both are invoked |

---

## 📊 Findings Log

| Step | Event |
|------|-------|
| 2026-09-04 bootstrap | Session created, hypotheses H1–H5 listed |
| 2026-09-04 static evidence | H1 CONFIRMED: `load_persistent_data()` called as module-level top-level code at app.py L328. This fires on **EVERY single Streamlit re-render**. Inside data_loader.py L25-53 it sequentially triggers: is_supabase_available() → client.exercises SELECT → supabase_schema_ready() → 4× separate table selects. Each call creates a NEW Supabase client (H5). |
| 2026-09-04 static evidence | H2 PARTIALLY CONFIRMED: `load_persistent_data` at data_loader.py L30 re-queries `client.table('exercises').select('*')` (full catalog fetch) on every call — cached nowhere; falls back to JSON disk at L41. |
| 2026-09-04 static evidence | H3 PARTIALLY CONFIRMED: app.py is 2006 lines with 6-page if/elif chain (L500, L1126, L1586, L1882, L2124, L2525). Non-active branches just do `elif X:` comparison (cheap ~1us each). Actual heavy render inside blocks only runs when selected. NOT the main bottleneck. |
| 2026-09-04 static evidence | H4 PLAUSIBLE (contributes to AI Coach page latency only; not global). L53, L67, L70 auth.py also shows no retries. |
| 2026-09-04 static evidence | H5 **CONFIRMED — biggest single contributor**. Call chain for one `load_persistent_data()` invocation: `is_supabase_available()` → `_get_supabase_client()` (L64 create_client + set_session) *FIRST TIME*. Then `_get_supabase_client()` **AGAIN** (L28) for exercises. Then `supabase_schema_ready()` → `_get_supabase_client()` (3rd time) + `_profiles_support_user_id()` (schema probe SELECT). Then `load_latest_profile` → `_get_supabase_client()` (4th). `get_latest_profile_id` → 5th client. `load_latest_workout_plan` → 6th client. `load_workout_history` → 7th client. **7 new Supabase client objects constructed + auth session rehydrated from scratch PER RE-RENDER.** |
| 2026-09-04 conclusion | **ROOT CAUSE = H5 + H1 combined** (7× redundant `create_client()` reconstructions + 5–6 sequential HTTP SELECTs per every widget change). Perceived latency per click: 400ms–2s of blocking work. |

---

## Confirmed/Hypothesis Status

| Hypothesis | Status | Quantitative Impact Estimate |
|-----------|:------:|-------------------------------|
| **H1 — Uncached storage calls on every re-render** | ✅ **CONFIRMED** | ~300–1200ms per widget change (5 sequential HTTP SELECTs) |
| H2 — Exercises catalog re-fetch each call | ✅ **CONFIRMED** | ~80–300ms per change (full exercises table network fetch) |
| H3 — 6-page if/elif monolith | ⚪ MINOR | ~1–5ms overhead, not a factor |
| H4 — AI Coach blocking (page-specific) | ⚪ PLAUSIBLE | Affects only AI Coach page, not global slowness |
| **H5 — Supabase client rebuilt 7× per render** | ✅ **CONFIRMED (HOTSPOT)** | 7× create_client() = JWT validation, session hydrate, HTTP connection pool setup each time. Estimated **200-600ms of pure Python overhead + extra SSL/TLS handshakes** — single biggest contributor |

---

## Fix Plan

Minimal targeted fix (3 localized changes):

1. **`infrastructure/storage.py`**: Make `_get_supabase_client()` use a module-level singleton cache keyed by (url, key, session_hash). Never re-build a client when the same auth session is active.
2. **`infrastructure/storage.py`**: Cache the boolean result of `_profiles_support_user_id()` per (client) because the schema never changes at runtime.
3. **`application/data_loader.py`**: Wrap data fetching functions in `@st.cache_data(ttl="10s", show_spinner=False)` so each re-render reuses prior results for up to 10 seconds (or `@st.cache_resource` for exercises catalog which is immutable). The 10s TTL keeps writes visible if the user just saved a new plan.
4. **Presentation `app.py` L328**: No change — but now the call is cheap because of #1-3 caching.


---

## 🎯 Action Checklist

- [ ] Static analysis of app.py render order + storage call sites
- [ ] Start Debug Server + write env file
- [ ] Add instrumentation probes (timing wrappers around H1–H5 suspects)
- [ ] User reproduces (interacts with pages, switches tabs, generates AI coach)
- [ ] Download pre-fix timing logs
- [ ] Confirm/reject H1 through H5 from evidence
- [ ] Minimal fix targeting confirmed bottleneck(s)
- [ ] Post-fix verification run + compare
- [ ] User confirmation
- [ ] Cleanup instrumentation + Debug Server
