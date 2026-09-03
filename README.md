# Multi-Tenant Personal Workout Trainer

> **"The ultimate objective of this platform isn't to chase hundreds of different trend-driven exercises. It is about staying disciplined, executing the right compound movements using intelligent AI coaching, and maintaining unwavering consistency. Cultivating physical discipline builds mental confidence - and that confidence rubs off on every other aspect of life itself."**

A robust, data-driven full-stack fitness management dashboard engineered to automate workout structuring, monitor muscle group training distribution, and keep secure multi-user states isolated. 

**Live Application:** https://personal-workout-trainer.streamlit.app/

---

## Tech Stack & System Architecture

- **Frontend & Core Engine:** [Streamlit](https://streamlit.io) (State-driven reactive interface)
- **Programming Language:** Python 3.11+
- **Cloud Backend & Database:** [Supabase](https://supabase.com) (PostgreSQL cloud storage data broker)
- **Authentication:** Custom Session-State Intercept Guards (Multi-tenant isolation)

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
+-- data/                       # Local profile storage & fallback caches
+-- config/
¦   +-- settings.py             # Central application paths and integration names
¦   +-- secrets.py              # Streamlit/.env/environment resolution
+-- domain/
¦   +-- workout_generation.py   # Pure exercise selection and plan generation
¦   +-- workout_validation.py   # Pure plan validation/duplicate detection
¦   +-- exercise_rules.py       # Pure exercise and history rules
¦   +-- performance.py          # Pure exercise performance aggregation
¦   +-- dashboard_metrics.py    # Pure dashboard calculations
+-- application/
¦   +-- data_loader.py          # Cloud-first bootstrap with local fallback
¦   +-- workout_plans.py        # Domain workout-plan use cases
+-- infrastructure/
¦   +-- json_repository.py      # Filesystem JSON persistence
¦   +-- storage.py              # Supabase adapter
+-- presentation/               # Streamlit presentation boundary
+-- modules/
¦   +-- ai_coach.py            # Fitness model engine routines
¦   +-- analytics.py             # Backward-compatible analytics facade
¦   +-- auth.py                # Multi-tenant validation gates
¦   +-- workout_generator.py   # Backward-compatible AI generator facade
¦   +-- workout_logger.py      # Real-time state logging panel
+-- services/
¦   +-- workout.py              # Backward-compatible pure generator facade
+-- utils/
¦   +-- helpers.py              # Backward-compatible helper facade
¦   +-- storage.py              # Backward-compatible storage facade
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
   pip install streamlit supabase
   streamlit run app.py
   ```
