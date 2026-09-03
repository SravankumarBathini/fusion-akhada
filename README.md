# Fusion Akhada

[![Live app](https://img.shields.io/badge/Live%20app-Streamlit-ff4b4b?logo=streamlit)](https://personal-workout-trainer.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?logo=python)](https://www.python.org/)

Fusion Akhada is an AI-assisted workout planning and progress-tracking application that blends
traditional Indian training methods with modern Western strength,
hypertrophy, and conditioning programming. Built with Streamlit, Google Gemini,
and Supabase.

> Build a plan, train consistently, and use your own performance data to guide
> the next session.

**Live application:** https://personal-workout-trainer.streamlit.app/

## Features

- Generates distinct split-aware weekly workout plans
- Combines Akhada-inspired strength, Vyayam conditioning, and Western training
  structures through Indian-Western program presets
- Tracks completed workouts, volume, streaks, and strength trends
- Adapts progression targets and equipment substitutions
- Provides beginner-friendly exercise instructions and coaching cues
- Isolates each user's profile, plan, and history with Supabase Auth and RLS
- Includes an administrator-only registration view

## Stack

- **UI:** [Streamlit](https://streamlit.io)
- **Language:** Python 3.11+
- **AI:** [Google Gemini](https://ai.google.dev/)
- **Database and auth:** [Supabase](https://supabase.com)
- **Tests:** Python `unittest`

## Architecture

The codebase separates pure business rules from integrations and presentation:

```text
config/          # Settings, secrets, and logging
domain/          # Pure workout generation, rules, validation, and metrics
application/     # Application use cases and cloud-first data loading
infrastructure/  # Supabase, JSON catalog, and registration adapters
presentation/    # Streamlit session-state boundary
modules/         # UI and backwards-compatible facades
database/        # Rerunnable Supabase migrations
tests/           # Regression tests
app.py           # Streamlit entry point
```

## Local setup

```powershell
git clone https://github.com/SravankumarBathini/personal-workout-trainer.git
cd personal-workout-trainer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
streamlit run app.py
```

Add your values to `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
GEMINI_API_KEY = "your-gemini-api-key"
```

Run `database/001_add_profile_ownership.sql` before using profiles. Run
`database/002_registration_events.sql` and configure the server-only
`SUPABASE_SERVICE_ROLE_KEY` plus `ADMIN_EMAIL` only if you need the admin
registration dashboard.

For Streamlit Community Cloud, add the same values under **App settings ->
Secrets**. Never commit `.streamlit/secrets.toml` or expose a service-role key.

## Validation

```powershell
python -m py_compile app.py
python -m unittest discover -s tests -v
```

## Safety and privacy

This project provides fitness education and planning, not medical advice.
Users should consult a qualified professional for injuries or medical
conditions. Supabase RLS policies enforce per-user access to profiles, plans,
and workout history.

## License

This project is released under the [MIT License](LICENSE).
