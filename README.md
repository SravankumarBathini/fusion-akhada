# 🏋️‍♂️ Multi-Tenant Personal Workout Trainer

A robust, data-driven full-stack fitness management dashboard engineered to automate workout structuring, monitor muscle group training distribution, and keep secure multi-user states isolated. 

🚀 **Live Application:** [Insert Your Streamlit Deployment URL Here]

---

## 🛠️ Tech Stack & System Architecture

- **Frontend & Core Engine:** [Streamlit](https://streamlit.io) (State-driven reactive interface)
- **Programming Language:** Python 3.11+
- **Cloud Backend & Database:** [Supabase](https://supabase.com) (PostgreSQL cloud storage data broker)
- **Authentication:** Custom Session-State Intercept Guards (Multi-tenant isolation)

---

## ⚡ Core Engineering Features

### 🔐 1. Multi-Tenant Gatekeeper Wall
Implements a strict interception pattern inside pp.py. If a user session is unauthenticated, the application dynamically replaces standard navigation routing parameters and injects customized CSS configurations to isolate the interface. Unauthorized users cannot execute underlying workout generation matrices or reach structural modules.

### 🧮 2. Automated Training Volume Pipeline
Tracks true workout load using a cumulative calculation thread: 
\\[\	ext{Training Volume} = \	ext{Weight (kg)} \	imes \	ext{Reps} \	imes \	ext{Sets}\\]
The platform aggregates data across metrics cards to visually graph total load, allowing fitness users to scale workouts effectively using verified, data-backed Progressive Overload.

### 📊 3. High-Fidelity Analytics Engine
Processes real-time workout logging inputs to display historical metrics including exercise distribution, streak thresholds, and personal records cleanly on the user dashboard.

---

## 📂 Project Workspace Topology

`	ext
├── .venv/                      # Isolated virtual environment
├── data/                       # Local profile storage & fallback caches
├── modules/
│   ├── ai_coach.py            # Fitness model engine routines
│   ├── analytics.py           # Training metrics & performance formulas
│   ├── auth.py                # Multi-tenant validation gates
│   ├── workout_generator.py   # Exercise selection & structural logic
│   └── workout_logger.py      # Real-time state logging panel
├── utils/
│   └── storage.py             # Database handshake routines
└── app.py                      # Reactive entry point & page layout
`

---

## 🚀 Local Installation & Setup

1. **Clone the Repository:**
   `ash
   git clone https://github.com
   cd personal-workout-trainer
   `

2. **Configure Your Environment:**
   `ash
   python -m venv .venv
   # Windows PowerShell activation:
   .\\.venv\\Scripts\\Activate.ps1
   # macOS/Linux activation:
   source .venv/bin/activate
   `

3. **Install Dependencies & Execute:**
   `ash
   pip install streamlit supabase
   streamlit run app.py
   `
