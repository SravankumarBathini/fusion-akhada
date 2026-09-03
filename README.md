# Multi-Tenant Personal Workout Trainer

> **"The ultimate objective of this platform isn't to chase hundreds of different trend-driven exercises. It is about staying disciplined, executing the right compound movements using intelligent AI coaching, and maintaining unwavering consistency. Cultivating physical discipline builds mental confidence - and that confidence rubs off on every other aspect of life itself."**

A robust, data-driven full-stack fitness management dashboard engineered to automate workout structuring, monitor muscle group training distribution, and keep secure multi-user states isolated. 

**Live Application:** https://personal-workout-trainer.streamlit.app/

---

## Tech Stack & System Architecture

- **Frontend & Core Engine:** [Streamlit](https://streamlit.io) (State-driven reactive interface)
- **Programming Language:** Python 3.11+
- **Cloud Backend & Database:** [Supabase](https://supabase.com) (PostgreSQL cloud storage data broker)
- **Authentication:** Supabase Auth with restored Streamlit session tokens

---

## Core Engineering Features

### 1. Multi-Tenant Gatekeeper Wall
Implements a strict interception pattern inside `app.py`. If a user session is unauthenticated, the application dynamically replaces standard navigation routing parameters and injects customized CSS configurations to isolate the interface. Unauthorized users cannot execute underlying workout generation matrices or reach structural modules.

### 2. Automated Training Volume Pipeline
Tracks true workout load using a cumulative calculation thread: 
`Training Volume = Weight (kg) × Reps × Sets`

The platform aggregates data across metrics cards to visually graph total load, allowing fitness users to scale workouts effectively using verified, data-backed Progressive Overload.

### 3. High-Fidelity Analytics Engine
Processes real-time workout logging inputs to display historical metrics including exercise distribution, streak thresholds, and personal records cleanly on the user dashboard.

---

## Project Workspace Topology

```text
+-- data/                       # Static exercise-catalog fallback only
+-- config/
+   +-- settings.py             # Central application paths and integration names
+   +-- secrets.py              # Streamlit/.env/environment resolution
+-- domain/
+   +-- workout_generation.py   # Pure exercise selection and plan generation
+   +-- workout_validation.py   # Pure plan validation/duplicate detection
+   +-- exercise_rules.py       # Pure exercise and history rules
+   +-- performance.py          # Pure exercise performance aggregation
+   +-- dashboard_metrics.py    # Pure dashboard calculations
+-- application/
+   +-- data_loader.py          # Cloud-first bootstrap and catalog fallback
+   +-- workout_plans.py        # Domain workout-plan use cases
+-- infrastructure/
+   +-- json_repository.py      # Filesystem JSON persistence
+   +-- storage.py              # Supabase adapter
+-- presentation/               # Streamlit presentation boundary
+-- modules/
+   +-- ai_coach.py            # Fitness model engine routines
+   +-- analytics.py           # Backward-compatible analytics facade
+   +-- auth.py                # Multi-tenant validation gates
+   +-- workout_generator.py   # Backward-compatible AI generator facade
+   +-- workout_logger.py      # Real-time state logging panel
+-- services/
+   +-- workout.py              # Backward-compatible pure generator facade
+-- utils/
+   +-- helpers.py              # Backward-compatible helper facade
+   +-- storage.py              # Backward-compatible storage facade
+-- app.py                      # Reactive entry point & page layout
```

The legacy `modules`, `services`, and `utils` import paths remain supported.
New reusable logic should be added to the corresponding `domain`,
`application`, `infrastructure`, or `config` package.

---

## Local Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/SravankumarBathini/personal-workout-trainer.git
   cd personal-workout-trainer
   ```

2. **Configure Your Environment:**
   ```bash
   python -m venv .venv
   # Windows PowerShell activation:
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux activation:
   source .venv/bin/activate
   ```

3. **Install Dependencies & Execute:**
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

4. **Configure Supabase:**
   - Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
   - Add your Supabase URL, anon key, and Gemini API key.
   - Run `database/001_add_profile_ownership.sql` in the Supabase SQL Editor.
     This enables RLS for profiles, workout plans, and workout history.
   - Confirm `profiles.user_id` exists before creating profiles.
   - Run `database/002_registration_events.sql` and configure the server-only
     `SUPABASE_SERVICE_ROLE_KEY` plus `ADMIN_EMAIL` to enable the admin dashboard.

For Streamlit Community Cloud, add the same values under
**App settings -> Secrets**. Never commit API keys or `.streamlit/secrets.toml`.

The hosted server configuration enables headless mode and CSRF protection,
disables usage-stat collection, and records authentication/storage diagnostics
without logging tokens or workout payloads.

## Validation

Run the built-in regression tests before deployment:

```bash
python -m unittest discover -s tests -v
```
