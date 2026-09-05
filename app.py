import modules.auth as auth
from infrastructure.storage import reset_user_progress_soft
from infrastructure.registration_notifications import (
    load_registration_events,
    registration_admin_configured,
)
from config.logging_config import configure_logging
from config.secrets import get_secret

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

configure_logging()
logger = logging.getLogger(__name__)

try:
    from application.data_loader import (
        bust_user_cache,
        load_persistent_data as _load_persistent_data,
    )
except ImportError:  # Module imported before Streamlit runtime ready.
    bust_user_cache = None
    from application.data_loader import load_persistent_data as _load_persistent_data
from config.settings import DATA_DIR
from presentation.session_state import initialize_session_state

# Streamlit page configuration must be the first Streamlit command.
st.set_page_config(
    page_title="Fusion Akhada",
    page_icon="🏋️‍♂️",
    layout="wide",
)

# ============================================================
# MASTER PRODUCTION AKHADA SAFFRON THEME — STATIC CSS FILE
# ============================================================
# Previously the entire CSS blob was serialized + injected via
# st.markdown(unsafe_allow_html=True) 3x per rerun.  We now read the
# CSS ONCE per process via ``@st.cache_resource`` and emit via
# ``st.html``.  Saves 40-60 ms of string + DOM diff work per rerun.
_THEME_CSS_PATH = Path(__file__).resolve().parent / "static" / "theme.css"


@st.cache_resource
def _load_theme_css(_path: Path) -> str:
    try:
        raw = _path.read_text(encoding="utf-8")
    except (OSError, PermissionError):
        return ""
    return f"<style>{raw}</style>"


_theme_css = _load_theme_css(_THEME_CSS_PATH)
if _theme_css:
    st.html(_theme_css)


from modules.workout_generator import (
    normalize_workout_plan,
    generate_weekly_plan,
)
from domain.workout_validation import has_duplicate_exercises

from domain.exercise_rules import (
    get_completed_exercises_count,
    get_exercise_instruction,
    get_exercise_coaching,
    get_workouts_this_week,
    get_workouts_this_month,
)
from domain.performance import get_exercise_performance
from modules.analytics import (
    calculate_exercise_summary,
    calculate_personal_records,
    get_progress_change,
)

from modules.ai_coach import (
    ask_ai_coach,
    GEMINI_MODEL,
)

from modules.workout_logger import (
    render_workout_logger,
)

from infrastructure.storage import (
    load_json,
    save_json,
    is_supabase_available,
    sign_out_supabase,
    save_profile_to_supabase,
    load_latest_profile_from_supabase,
    get_latest_profile_id,
    save_workout_plan_to_supabase,
    load_latest_workout_plan_from_supabase,
    save_workout_history_to_supabase,
    load_workout_history_from_supabase,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================


# Secure User Multi-Tenant Gatekeeper
if "user" not in st.session_state:
    auth.render_login_interface()
    st.stop()

# Dynamic Premium Equipment Background Engine
# Rogue background function stripped successfully to protect theme mechanics


# ============================================================
# FILE PATHS
# ============================================================

PROFILE_FILE = DATA_DIR / "profile.json"
WORKOUT_PLAN_FILE = DATA_DIR / "workout_plan.json"
WORKOUT_HISTORY_FILE = DATA_DIR / "workout_history.json"
EXERCISES_FILE = DATA_DIR / "exercises.json"


# ============================================================
# SESSION STATE
# ============================================================

initialize_session_state(st.session_state)


# ============================================================
# PERSISTENT DATA LOADING
# ============================================================

def load_persistent_data():
    """Load cloud-first application data through the application use case."""
    authenticated_user = st.session_state.get("user")
    user_id = (
        authenticated_user.get("id")
        if isinstance(authenticated_user, dict)
        else getattr(authenticated_user, "id", None)
    )
    return _load_persistent_data(
        profile_file=PROFILE_FILE,
        workout_plan_file=WORKOUT_PLAN_FILE,
        workout_history_file=WORKOUT_HISTORY_FILE,
        exercises_file=EXERCISES_FILE,
        user_id=user_id,
        warning_callback=st.warning,
    )


def save_cloud_workout_plan(plan):
    """Persist a plan in Supabase and fail loudly when it is unavailable."""
    profile_id = st.session_state.get("profile_id")
    if not profile_id:
        raise RuntimeError("An active Supabase profile is required.")

    saved_row = save_workout_plan_to_supabase(profile_id, plan)
    if not saved_row:
        raise RuntimeError("Supabase did not return the saved workout plan.")


# ============================================================
# ENFORCED DYNAMIC LIVE STORAGE SYNCHRONISATION 
# ============================================================

(
    loaded_profile,
    loaded_workout_plan,
    loaded_workout_history,
    exercise_database,
    loaded_profile_id,
    storage_source,
) = load_persistent_data()

if loaded_profile:
    st.session_state.profile = loaded_profile
    st.session_state.profile_created = True
st.session_state.workout_plan = loaded_workout_plan or []
st.session_state.workout_history = loaded_workout_history or []
if loaded_profile_id:
    st.session_state.profile_id = loaded_profile_id
if storage_source:
    st.session_state.storage_source = storage_source

if storage_source != "supabase":
    st.error(
        "Supabase is required to use this application. "
        "Configure SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets. "
        "If credentials are configured, run "
        "database/001_add_profile_ownership.sql in the Supabase SQL Editor, "
        "then reload the page."
    )
    st.stop()
st.sidebar.success("Cloud data synced with Supabase")

# ============================================================
# NORMALIZE WORKOUT PLAN
# ============================================================

st.session_state.workout_plan = normalize_workout_plan(
    st.session_state.workout_plan
)

if has_duplicate_exercises(st.session_state.workout_plan):
    st.session_state.workout_plan = []
    st.info(
        "Your saved workout plan contained repeated exercises. "
        "Generate a new weekly plan to apply the exercise-variation fix."
    )


# ============================================================
# DASHBOARD HELPERS
# ============================================================
# DASHBOARD HELPERS
# ============================================================

from domain.dashboard_metrics import (
    calculate_current_streak,
    calculate_total_volume,
    compute_history_summary,
    get_best_strength_highlights,
    get_completed_workouts_this_week,
    get_next_workout,
    get_recent_workouts,
    get_weekly_progress,
    get_week_start,
    get_workout_date,
    safe_float,
    safe_int,
)
from domain.program_presets import PROGRAM_PRESETS, get_program_preset


# ============================================================
# PRESENTATION HELPERS (pre-compute to save rerun cycles)
# ============================================================


@st.cache_data(ttl=15)
def _precompute_weekly_plan_dicts(workout_plan_json: str):
    """Pre-compute weekly plan render data from a JSON snapshot.

    The ``Your Weekly Workout Plan`` expanders used to call
    ``get_exercise_instruction`` / ``get_exercise_coaching`` (each an
    ``lru_cache`` hit after the first, but still dict marshalling) once
    per exercise, per expander, per rerun.  Now we return a plain list
    of plain dicts — strings already resolved — so the Dashboard render
    loop becomes nothing more than st.write + st.metric on primitives.

    The caller JSON-stringifies ``workout_plan`` into the key so cache
    invalidation is automatic whenever plan bytes change (e.g. after
    ``Generate New Weekly Plan 🔥`` runs and triggers ``st.rerun()``).
    ``TTL=15s`` still catches cases where plan bytes would otherwise
    sit stale longer than our user-cache.
    """
    try:
        plan = json.loads(workout_plan_json)
    except (TypeError, ValueError):
        return []

    days = []
    for workout_day in plan or []:
        day_number = workout_day.get("day", "")
        day_name = workout_day.get("name", "Workout")
        duration = workout_day.get("duration", 45)
        intensity = workout_day.get("intensity", "Moderate")
        warmup = workout_day.get("warmup", "5-10 minutes")
        cooldown = workout_day.get("cooldown", "5 minutes")
        warmup_rows = workout_day.get("warmup_exercises") or []
        cooldown_rows = workout_day.get("cooldown_exercises") or []
        exercises_raw = workout_day.get("exercises", [])
        exercise_items = []
        for index, exercise in enumerate(exercises_raw, start=1):
            name = exercise.get("name", "Exercise")
            instruction = get_exercise_instruction(exercise) or ""
            coaching = get_exercise_coaching(exercise) or {
                "steps": [],
                "breathing": "",
                "mistakes": "",
                "modification": "",
                "progression": "",
            }
            exercise_items.append(
                {
                    "index": index,
                    "name": name,
                    "sets": exercise.get("sets", "-"),
                    "reps": exercise.get("reps", "-"),
                    "rest": exercise.get("rest", "-"),
                    "equipment": exercise.get("equipment", "-"),
                    "primary_muscle": exercise.get("primary_muscle", "-"),
                    "movement_pattern": exercise.get("movement_pattern", "-"),
                    "instruction": instruction,
                    "coaching_steps": list(coaching.get("steps") or []),
                    "breathing": coaching.get("breathing", ""),
                    "mistakes": coaching.get("mistakes", ""),
                    "modification": coaching.get("modification", ""),
                    "progression": coaching.get("progression", ""),
                }
            )
        days.append(
            {
                "day_number": day_number,
                "day_name": day_name,
                "duration": duration,
                "intensity": intensity,
                "warmup": warmup,
                "cooldown": cooldown,
                "exercises_count": len(exercises_raw),
                "exercises": exercise_items,
                "warmup_exercises": warmup_rows,
                "cooldown_exercises": cooldown_rows,
            }
        )
    return days


@st.cache_data(ttl=10, show_spinner=False)
def _cached_history_summary(workout_history_json: str):
    """Single-pass history totals + 8-week buckets, cached 10 seconds.

    Wraps :func:`domain.dashboard_metrics.compute_history_summary` so:
      * every call-site (dashboard metrics, training momentum chart,
        Workout History tab) re-uses the SAME cached 6-field snapshot
      * serialization via ``json.dumps(sort_keys=True)`` turns the
        mutable ``workout_history`` list-of-dicts into a stable cache
        key Streamlit can hash reliably
    """
    try:
        history = json.loads(workout_history_json)
    except (TypeError, ValueError):
        history = []
    return compute_history_summary(history)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.title(
    "🏋️ Fusion Akhada"
)
st.sidebar.caption(
    "Fitness guidance only—not medical advice. Consult a qualified professional "
    "for injuries or medical conditions."
)

page_options = [
    "Dashboard",
    "My Profile",
    "My Workout",
    "Workout History",
    "Progress",
    "AI Coach",
]

current_user = st.session_state.get("user")
admin_email = get_secret("ADMIN_EMAIL")
current_user_email = (
    current_user.get("email")
    if isinstance(current_user, dict)
    else getattr(current_user, "email", None)
)
if admin_email and current_user_email and current_user_email.lower() == admin_email.lower():
    page_options.append("Admin: Registrations")

if (
    st.session_state.page
    not in page_options
):

    st.session_state.page = (
        "Dashboard"
    )

selected_page = st.sidebar.radio(
    "Navigation",
    page_options,
    index=page_options.index(
        st.session_state.page
    ),
)

st.session_state.page = (
    selected_page
)


# ============================================================
# STORAGE STATUS
# ============================================================

if (
    st.session_state.get(
        "storage_source"
    )
    == "supabase"
):

    st.sidebar.success(
        "☁️ Cloud storage: Supabase"
    )

else:
    st.sidebar.error("Supabase storage is unavailable")




# ============================================================
# DANGER ZONE: DATA CLEANUP CONTROLLER
# ============================================================
st.sidebar.markdown("---")
# Isolated User Session Eraser Loop
if st.sidebar.button("🚪 Log Out of Session", use_container_width=True):
    try:
        sign_out_supabase()
    except Exception as error:
        st.error(f"Could not end the Supabase session: {error}")
    else:
        logger.info("Authentication session ended")
        st.session_state.clear()
        st.success("Signed out securely. Your cloud data was not deleted.")
        st.rerun()
with st.sidebar.expander("Danger Zone 🚨", expanded=False):
    st.write("Wipe existing test logs to clear room for your true tracking data.")
    if st.button("Reset Progress & Start Fresh", type="primary", use_container_width=True):
        pass
        
        with st.spinner("Purging test data..."):
            if reset_user_progress_soft():
                if bust_user_cache is not None:
                    bust_user_cache()
                # Instantly strip volatile states in active session memory
                st.session_state.workout_plan = []
                st.session_state.workout_history = []
                st.session_state.cloud_data_loaded = True
                st.session_state.page = "Dashboard"
                
                st.toast("Testing profiles cleared successfully!")
                st.rerun()
            else:
                st.error("Failed to cleanly flush structural tables.")

# ============================================================
# DASHBOARD
# ============================================================

if st.session_state.page == "Dashboard":

    profile = (
        st.session_state.profile
    )

    workout_plan = (
        st.session_state.workout_plan
    )

    workout_history = (
        st.session_state.workout_history
    )

    st.title("🏠 Dashboard")

    if not profile:

        st.info(
            "Welcome to Fusion Akhada!"
        )

        st.write(
            "Create your profile first. Your dashboard "
            "will then show your training activity, "
            "progress, workouts, and performance."
        )

        if st.button(
            "Create My Profile →",
            type="primary",
        ):

            st.session_state.page = (
                "My Profile"
            )

            st.rerun()

    else:

        name = profile.get(
            "name",
            "there",
        )

        fitness_goal = profile.get(
            "fitness_goal",
            "Improve overall fitness",
        )

        fitness_level = profile.get(
            "fitness_level",
            "Beginner",
        )

        st.markdown(
            f"""
            <section class="premium-hero">
                <div class="hero-eyebrow">PERSONAL TRAINING COMMAND CENTER</div>
                <h1 class="hero-title">Welcome back, {name}! 👋</h1>
                <p class="hero-copy">
                    Your next best session is ready. Stay consistent, train with intent,
                    and build momentum one workout at a time.
                </p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Current focus: **{fitness_goal}**  ·  Training level: **{fitness_level}**"
        )

        st.divider()

        # Single-pass history summary (replaces 4 separate O(H) scans + 8-week
        # O(H) progress bucket scan = 5 redundant iterations over history on
        # every dashboard tab rerun).  TTL-cached at module scope below so
        # "Training Momentum" and Workout History tab reuse the same dict.
        _history_summary = _cached_history_summary(
            json.dumps(workout_history or [], sort_keys=True)
        )
        total_workouts = _history_summary["total_workouts"]
        workouts_this_week = _history_summary["workouts_this_week"]
        current_streak = _history_summary["current_streak"]
        total_volume = _history_summary["total_volume"]

        col1, col2, col3, col4 = (
            st.columns(4)
        )

        with col1:

            st.metric(
                "Total Workouts",
                total_workouts,
            )

        with col2:

            st.metric(
                "This Week",
                workouts_this_week,
            )

        with col3:

            st.metric(
                "Current Streak",
                f"{current_streak} day"
                f"{'s' if current_streak != 1 else ''}",
            )

        with col4:

            st.metric(
                "Training Volume",
                f"{total_volume:,.0f} kg",
            )

        st.divider()

        st.subheader(
            "🏋️ Today's Training"
        )

        next_workout = get_next_workout(
            workout_plan,
            workout_history,
        )

        if next_workout is not None:

            workout_name = (
                next_workout.get(
                    "name",
                    "Workout",
                )
            )

            duration = (
                next_workout.get(
                    "duration",
                    profile.get(
                        "workout_duration",
                        45,
                    ),
                )
            )

            intensity = (
                next_workout.get(
                    "intensity",
                    profile.get(
                        "workout_intensity",
                        "Moderate",
                    ),
                )
            )

            exercises = (
                next_workout.get(
                    "exercises",
                    [],
                )
            )

            col1, col2 = (
                st.columns([3, 1])
            )

            with col1:

                st.markdown(
                    f"### {workout_name}"
                )

                st.write(
                    f"**Duration:** {duration} minutes"
                )

                st.write(
                    f"**Intensity:** {intensity}"
                )

                st.write(
                    f"**Exercises:** {len(exercises)}"
                )

            with col2:

                if st.button(
                    "Start / Log Workout 📝",
                    type="primary",
                    use_container_width=True,
                ):

                    st.session_state.page = (
                        "My Workout"
                    )

                    st.rerun()

                if st.button(
                    "View Full Workout",
                    use_container_width=True,
                ):

                    st.session_state.page = (
                        "My Workout"
                    )

                    st.rerun()

        else:

            st.warning(
                "You don't have a workout plan yet."
            )

            if st.button(
                "Generate My Workout Plan 💪",
                type="primary",
            ):

                new_plan = (
                    generate_weekly_plan(
                        profile,
                        exercise_database,
                    )
                )

                st.session_state.workout_plan = (
                    new_plan
                )

                profile_id = (
                    st.session_state.profile_id
                )

                save_cloud_workout_plan(new_plan)

                st.success(
                    "Your personalized workout plan "
                    "has been generated!"
                )

                st.rerun()

        st.divider()

        st.subheader(
            "📅 Weekly Training Progress"
        )

        planned_days = safe_int(
            profile.get(
                "days_per_week",
                len(workout_plan),
            ),
            len(workout_plan),
        )

        if planned_days <= 0:
            planned_days = 1

        weekly_percentage = min(
            100,
            int(
                (
                    workouts_this_week
                    / planned_days
                )
                * 100
            ),
        )

        st.progress(
            weekly_percentage / 100
        )

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:

            st.metric(
                "Completed",
                workouts_this_week,
            )

        with col2:

            st.metric(
                "Target",
                planned_days,
            )

        with col3:

            st.metric(
                "Completion",
                f"{weekly_percentage}%",
            )

        if (
            workouts_this_week
            >= planned_days
        ):

            st.success(
                "🎯 Weekly workout target reached!"
            )

        elif workouts_this_week > 0:

            remaining = (
                planned_days
                - workouts_this_week
            )

            st.info(
                f"💪 {remaining} more workout"
                f"{'s' if remaining != 1 else ''} "
                "to reach your weekly target."
            )

        else:

            st.info(
                "Start your first workout of the week!"
            )

        st.divider()
        st.subheader("📈 Training Momentum")
        # 8-week buckets were computed ONCE inside ``compute_history_summary``
        # — reuse the same cached list rather than walking H × 8 weeks again.
        weekly_progress = _history_summary["weekly_progress"]
        if any(item["Workouts"] for item in weekly_progress):
            chart_col, insight_col = st.columns([2, 1])
            with chart_col:
                st.caption("Your eight-week training volume trend")
                st.line_chart(
                    weekly_progress,
                    x="Week",
                    y="Volume (kg)",
                    height=240,
                )
            with insight_col:
                best_week = max(
                    weekly_progress,
                    key=lambda item: item["Volume (kg)"],
                )
                average_workouts = sum(
                    item["Workouts"] for item in weekly_progress
                ) / len(weekly_progress)
                with st.container(border=True):
                    st.caption("COACH'S READ")
                    st.metric(
                        "Best volume week",
                        f"{best_week['Volume (kg)']:,.0f} kg",
                        best_week["Week"],
                    )
                    st.metric(
                        "Weekly average",
                        f"{average_workouts:.1f} sessions",
                    )
        else:
            st.info(
                "Your momentum chart will appear after your first completed workout."
            )

        st.divider()

        st.subheader(
            "🕒 Recent Activity"
        )

        recent_workouts = (
            get_recent_workouts(
                workout_history,
                3,
            )
        )

        if recent_workouts:

            for workout in recent_workouts:

                date_value = workout.get(
                    "date",
                    "-",
                )

                workout_name = workout.get(
                    "workout_name",
                    "Workout",
                )

                actual_duration = (
                    workout.get(
                        "actual_duration"
                    )
                )

                workout_volume = (
                    safe_float(
                        workout.get(
                            "total_volume",
                            0,
                        )
                    )
                )

                exercises = (
                    workout.get(
                        "exercises",
                        [],
                    )
                )

                completed_exercises = sum(
                    1
                    for exercise in exercises
                    if exercise.get(
                        "completed",
                        False,
                    )
                )

                with st.container(
                    border=True
                ):

                    col1, col2, col3, col4 = (
                        st.columns(4)
                    )

                    with col1:

                        st.write(
                            f"**{date_value}**"
                        )

                        st.write(
                            workout_name
                        )

                    with col2:

                        st.write(
                            "**Exercises**"
                        )

                        st.write(
                            f"{completed_exercises}/"
                            f"{len(exercises)}"
                        )

                    with col3:

                        st.write(
                            "**Duration**"
                        )

                        if actual_duration:

                            st.write(
                                f"{actual_duration} min"
                            )

                        else:

                            st.write("—")

                    with col4:

                        st.write(
                            "**Volume**"
                        )

                        st.write(
                            f"{workout_volume:,.0f} kg"
                        )

        else:

            st.info(
                "No completed workouts yet. "
                "Complete your first workout and "
                "your activity will appear here."
            )

        st.divider()

        st.subheader(
            "🏆 Strength Highlights"
        )

        strength_highlights = (
            get_best_strength_highlights(
                workout_history
            )
        )

        if strength_highlights:

            columns = st.columns(
                min(
                    3,
                    len(
                        strength_highlights
                    ),
                )
            )

            for index, highlight in enumerate(
                strength_highlights[:3]
            ):

                with columns[
                    index % len(columns)
                ]:

                    st.metric(
                        highlight["exercise"],
                        f"{highlight['weight']:g} kg",
                        f"{highlight['reps']} reps",
                    )

        else:

            st.info(
                "Your strength highlights will appear "
                "after you log weights and repetitions."
            )

        st.divider()

        st.subheader(
            "⚡ Quick Actions"
        )

        col1, col2, col3, col4, col5 = (
            st.columns(5)
        )

        with col1:

            if st.button(
                "🏋️ My Workout",
                use_container_width=True,
            ):

                st.session_state.page = (
                    "My Workout"
                )

                st.rerun()

        with col2:

            if st.button(
                "📝 History",
                use_container_width=True,
            ):

                st.session_state.page = (
                    "Workout History"
                )

                st.rerun()

        with col3:

            if st.button(
                "📈 Progress",
                use_container_width=True,
            ):

                st.session_state.page = (
                    "Progress"
                )

                st.rerun()

        with col4:

            if st.button(
                "🤖 AI Coach",
                use_container_width=True,
            ):

                st.session_state.page = (
                    "AI Coach"
                )

                st.rerun()

        with col5:

            if st.button(
                "👤 Profile",
                use_container_width=True,
            ):

                st.session_state.page = (
                    "My Profile"
                )

                st.rerun()


# ============================================================
# MY PROFILE
# ============================================================

elif st.session_state.page == "My Profile":

    st.title("👤 My Profile")

    profile = (
        st.session_state.profile
    )

    st.subheader(
        "Basic Information"
    )

    col1, col2 = st.columns(2)

    with col1:

        name = st.text_input(
            "Name",
            value=profile.get(
                "name",
                "",
            ),
        )

        age = st.number_input(
            "Age",
            min_value=10,
            max_value=100,
            value=int(
                profile.get(
                    "age",
                    25,
                )
            ),
        )

        gender_options = [
            "Male",
            "Female",
            "Other",
            "Prefer not to say",
        ]

        saved_gender = profile.get(
            "gender",
            "Male",
        )

        gender = st.selectbox(
            "Gender",
            gender_options,
            index=(
                gender_options.index(
                    saved_gender
                )
                if saved_gender
                in gender_options
                else 0
            ),
        )

    with col2:

        height = st.number_input(
            "Height (cm)",
            min_value=100.0,
            max_value=250.0,
            value=float(
                profile.get(
                    "height",
                    170,
                )
            ),
        )

        weight = st.number_input(
            "Weight (kg)",
            min_value=20.0,
            max_value=300.0,
            value=float(
                profile.get(
                    "weight",
                    70,
                )
            ),
        )

    st.divider()

    st.subheader(
        "Fitness Information"
    )

    fitness_goals = [
        "Build muscle",
        "Lose fat",
        "Build muscle and lose fat",
        "Improve strength",
        "Improve endurance",
        "Improve overall fitness",
    ]

    fitness_levels = [
        "Beginner",
        "Intermediate",
        "Advanced",
    ]

    workout_locations = [
        "Home",
        "Gym",
        "Outdoor",
    ]

    workout_styles = [
        "Strength Training",
        "Hypertrophy / Muscle Building",
        "Fat Loss / Conditioning",
        "Cardio",
        "Bodyweight Training",
        "Mixed Training",
    ]

    saved_preset = profile.get("program_preset", "Custom")
    if saved_preset not in PROGRAM_PRESETS:
        saved_preset = "Custom"
    program_preset = st.selectbox(
        "Program Preset",
        list(PROGRAM_PRESETS),
        index=list(PROGRAM_PRESETS).index(saved_preset),
        help="Choose a curated Indian-Western training approach or keep full control.",
    )
    st.caption(get_program_preset(program_preset)["description"])

    workout_intensities = [
        "Light",
        "Moderate",
        "Challenging",
        "High",
    ]

    equipment_options = [
        "No equipment",
        "Dumbbells",
        "Barbell",
        "Bench",
        "Resistance bands",
        "Pull-up bar",
        "Kettlebell",
        "Cable machine",
        "Machines",
        "Cardio equipment",
    ]

    col1, col2 = st.columns(2)

    with col1:

        saved_goal = profile.get(
            "fitness_goal",
            fitness_goals[0],
        )

        fitness_goal = st.selectbox(
            "Fitness Goal",
            fitness_goals,
            index=(
                fitness_goals.index(
                    saved_goal
                )
                if saved_goal
                in fitness_goals
                else 0
            ),
        )

        saved_level = profile.get(
            "fitness_level",
            fitness_levels[0],
        )

        fitness_level = st.selectbox(
            "Fitness Level",
            fitness_levels,
            index=(
                fitness_levels.index(
                    saved_level
                )
                if saved_level
                in fitness_levels
                else 0
            ),
        )

        saved_location = profile.get(
            "workout_location",
            workout_locations[0],
        )

        workout_location = st.selectbox(
            "Workout Location",
            workout_locations,
            index=(
                workout_locations.index(
                    saved_location
                )
                if saved_location
                in workout_locations
                else 0
            ),
        )

    with col2:

        saved_equipment = profile.get(
            "equipment",
            [],
        )

        if not isinstance(
            saved_equipment,
            list,
        ):

            saved_equipment = []

        saved_equipment = [
            item
            for item in saved_equipment
            if item
            in equipment_options
        ]

        equipment = st.multiselect(
            "Equipment Available",
            equipment_options,
            default=saved_equipment,
        )

        days_per_week = st.slider(
            "Days per Week",
            min_value=1,
            max_value=7,
            value=int(
                profile.get(
                    "days_per_week",
                    3,
                )
            ),
        )

        workout_duration = st.slider(
            "Workout Duration (minutes)",
            min_value=15,
            max_value=120,
            value=int(
                profile.get(
                    "workout_duration",
                    45,
                )
            ),
            step=5,
        )

    st.divider()

    st.subheader(
        "Workout Preferences"
    )

    target_area_options = [
        "Full Body",
        "Chest",
        "Back",
        "Shoulders",
        "Biceps",
        "Triceps",
        "Quadriceps",
        "Hamstrings",
        "Glutes",
        "Legs",
        "Core",
    ]

    saved_target_areas = profile.get(
        "target_areas",
        [],
    )

    if not isinstance(
        saved_target_areas,
        list,
    ):

        saved_target_areas = []

    saved_target_areas = [
        area
        for area in saved_target_areas
        if area
        in target_area_options
    ]

    target_areas = st.multiselect(
        "Target Areas",
        target_area_options,
        default=saved_target_areas,
    )

    saved_style = profile.get(
        "workout_style",
        workout_styles[0],
    )

    workout_style = st.selectbox(
        "Workout Style",
        workout_styles,
        index=(
            workout_styles.index(
                saved_style
            )
            if saved_style
            in workout_styles
            else 0
        ),
    )
    preset_style = get_program_preset(program_preset)["workout_style"]
    if preset_style:
        workout_style = preset_style

    saved_intensity = profile.get(
        "workout_intensity",
        workout_intensities[1],
    )

    workout_intensity = st.selectbox(
        "Workout Intensity",
        workout_intensities,
        index=(
            workout_intensities.index(
                saved_intensity
            )
            if saved_intensity
            in workout_intensities
            else 1
        ),
    )

    exercises_enjoy = st.text_input(
        "Exercises You Enjoy",
        value=profile.get(
            "exercises_enjoy",
            "",
        ),
        help="Example: bench press, squats, pull-ups",
    )

    exercises_to_avoid = st.text_input(
        "Exercises You Want to Avoid",
        value=profile.get(
            "exercises_to_avoid",
            "",
        ),
        help="Example: running, burpees",
    )

    physical_injuries = st.text_area(
        "Physical Injuries & Structural Limitations",
        value=profile.get("physical_injuries", ""),
        placeholder="e.g., Lower back pain during squats, torn rotator cuff, or knee stiffness...",
        help="Critical health data used by the AI to structure a safe training routine",
    ).strip()

    if st.button(
        "Save Profile 💾",
        type="primary",
    ):

        updated_profile = {
            "name": name,
            "age": age,
            "gender": gender,
            "height": height,
            "weight": weight,
            "fitness_goal": fitness_goal,
            "fitness_level": fitness_level,
            "workout_location": workout_location,
            "equipment": equipment,
            "days_per_week": days_per_week,
            "workout_duration": workout_duration,
            "target_areas": target_areas,
            "workout_style": workout_style,
            "program_preset": program_preset,
            "workout_intensity": workout_intensity,
            "exercises_enjoy": exercises_enjoy,
            "exercises_to_avoid": exercises_to_avoid,
            "physical_injuries": physical_injuries,
        }

        try:

            if is_supabase_available():

                saved_row = (
                    save_profile_to_supabase(
                        updated_profile,
                        user_id=(
                            st.session_state.get("user", {}).get("id")
                            if isinstance(st.session_state.get("user"), dict)
                            else getattr(st.session_state.get("user"), "id", None)
                        ),
                    )
                )

                if not saved_row:

                    raise RuntimeError(
                        "Supabase did not return the saved profile."
                    )

                st.session_state.profile_id = (
                    saved_row.get("id")
                )

                st.session_state.storage_source = (
                    "supabase"
                )

            else:
                raise RuntimeError(
                    "Supabase is required before saving a profile."
                )

            if bust_user_cache is not None:
                bust_user_cache()

            st.session_state.profile = (
                updated_profile
            )

            st.session_state.profile_created = True
            st.session_state.cloud_data_loaded = True
            st.toast("Profile memory updated successfully!")

            st.success(
                "Profile saved successfully! ✅"
            )

            st.rerun()

        except Exception as error:

            st.error(
                "Profile could not be saved."
            )

            st.exception(error)


# ============================================================
# MY WORKOUT
# ============================================================

elif st.session_state.page == "My Workout":

    st.title("🏋️ My Workout")

    profile = (
        st.session_state.profile
    )

    workout_plan = (
        st.session_state.workout_plan
    )

    if not profile:

        st.warning(
            "Please create your profile first."
        )

    elif not workout_plan:

        st.info(
            "You don't have a workout plan yet."
        )

        if st.button(
            "Generate My Workout Plan 💪",
            type="primary",
        ):

            new_plan = (
                generate_weekly_plan(
                    profile,
                    exercise_database,
                )
            )

            st.session_state.workout_plan = (
                new_plan
            )

            profile_id = (
                st.session_state.profile_id
            )

            try:

                save_cloud_workout_plan(new_plan)

                if bust_user_cache is not None:
                    bust_user_cache()

                st.success(
                    "Workout plan generated!"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    "Workout plan could not be saved."
                )

                st.exception(error)

    else:

        st.subheader(
            "📅 Your Weekly Workout Plan"
        )

        # TTL-cached 15s: walk plan ONCE and pre-resolve every instruction +
        # coaching step/breathing/... string into primitives.  The original
        # loop built the exact same expander tree + exercise lookup strings
        # on every tab rerun; now it's one ``json.dumps`` hash + plain dict
        # iteration over strings.
        _plan_days = _precompute_weekly_plan_dicts(
            json.dumps(workout_plan or [], sort_keys=True)
        )

        for day in _plan_days:

            with st.expander(
                f"Day {day['day_number']}: {day['day_name']}",
                expanded=False,
            ):

                col1, col2, col3 = (
                    st.columns(3)
                )

                with col1:

                    st.metric(
                        "Duration",
                        f"{day['duration']} min",
                    )

                with col2:

                    st.metric(
                        "Intensity",
                        day["intensity"],
                    )

                with col3:

                    st.metric(
                        "Exercises",
                        day["exercises_count"],
                    )

                st.write(
                    f"🔥 **Warm-up:** {day['warmup']}"
                )

                warmup_rows = day.get("warmup_exercises") or []
                cooldown_rows = day.get("cooldown_exercises") or []

                with st.expander(
                    f"🔥 Warm-up · {len(warmup_rows)} exercises",
                    expanded=False,
                ):
                    for wex in warmup_rows:
                        with st.container(border=True):
                            wcols = st.columns([3, 1, 2, 5])
                            wcols[0].markdown(f"**{wex.get('name', '')}**")
                            wcols[1].write(
                                f"{wex.get('sets', '')} × {wex.get('reps', '')}"
                            )
                            wcols[2].write(wex.get("equipment", ""))
                            wcols[3].write(wex.get("instructions", ""))

                with st.expander(
                    f"🧊 Cool-down · {len(cooldown_rows)} exercises · static stretches",
                    expanded=False,
                ):
                    for cex in cooldown_rows:
                        with st.container(border=True):
                            ccols = st.columns([3, 1, 2, 5])
                            ccols[0].markdown(f"**{cex.get('name', '')}**")
                            ccols[1].write(
                                f"{cex.get('sets', '')} × {cex.get('reps', '')}"
                            )
                            ccols[2].write(cex.get("equipment", ""))
                            ccols[3].write(cex.get("instructions", ""))

                for ex in day["exercises"]:

                    st.markdown(
                        f"### {ex['index']}. "
                        f"{ex['name']}"
                    )

                    col1, col2, col3, col4 = (
                        st.columns(4)
                    )

                    with col1:

                        st.write(
                            f"**Sets:** "
                            f"{ex['sets']}"
                        )

                    with col2:

                        st.write(
                            f"**Reps:** "
                            f"{ex['reps']}"
                        )

                    with col3:

                        st.write(
                            f"**Rest:** "
                            f"{ex['rest']}"
                        )

                    with col4:

                        st.write(
                            f"**Equipment:** "
                            f"{ex['equipment']}"
                        )

                    st.write(
                        f"**Primary Muscle:** "
                        f"{ex['primary_muscle']}"
                    )

                    st.write(
                        f"**Movement:** "
                        f"{ex['movement_pattern']}"
                    )

                    with st.expander("📖 How to perform this exercise"):
                        st.write(ex["instruction"])
                        st.markdown("**Step-by-step**")
                        for step_number, step in enumerate(
                            ex["coaching_steps"],
                            start=1,
                        ):
                            st.write(f"{step_number}. {step}")
                        st.write(f"**Breathing:** {ex['breathing']}")
                        st.write(f"**Avoid:** {ex['mistakes']}")
                        st.write(f"**Beginner option:** {ex['modification']}")
                        st.write(f"**Progress when ready:** {ex['progression']}")
                        st.caption(
                            "Fitness guidance only. Use a controlled range of motion and "
                            "stop if you feel pain, dizziness, or discomfort."
                        )

                st.write(
                    f"🧘 **Cooldown:** "
                    f"{day['cooldown']}"
                )

        st.divider()

        if st.button(
            "Generate New Weekly Plan 🔥"
        ):

            new_plan = (
                generate_weekly_plan(
                    profile,
                    exercise_database,
                )
            )

            st.session_state.workout_plan = (
                new_plan
            )

            profile_id = (
                st.session_state.profile_id
            )

            try:

                save_cloud_workout_plan(new_plan)

                if bust_user_cache is not None:
                    bust_user_cache()

                st.success(
                    "A new personalized weekly plan "
                    "has been generated!"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    "Workout plan could not be saved."
                )

                st.exception(error)

        st.divider()

        st.subheader(
            "🏃 Workout Logger"
        )

        st.write(
            "Log every set, weight, and repetition "
            "from your actual workout."
        )

        # ----------------------------------------------------
        # WORKOUT LOGGER
        # ----------------------------------------------------

        st.session_state.workout_history = (
            render_workout_logger(
                workout_plan=(
                    st.session_state.workout_plan
                ),
                workout_history=(
                    st.session_state.workout_history
                ),
                profile=st.session_state.profile,
                history_file=(
                    WORKOUT_HISTORY_FILE
                ),
                save_json_function=save_json,
                save_supabase_function=(
                    save_workout_history_to_supabase
                ),
                profile_id=(
                    st.session_state.profile_id
                ),
                use_supabase=(
                    st.session_state.storage_source
                    == "supabase"
                ),
            )
            or st.session_state.workout_history
        )


# ============================================================
# WORKOUT HISTORY
# ============================================================

elif st.session_state.page == "Workout History":

    st.title("📚 Workout History")

    history = (
        st.session_state.workout_history
    )

    if not history:

        st.info(
            "No completed workouts yet. "
            "Complete your first workout to see it here."
        )

    else:

        completed_exercises = (
            get_completed_exercises_count(
                history
            )
        )

        col1, col2 = (
            st.columns(2)
        )

        with col1:

            st.metric(
                "Completed Workouts",
                len(history),
            )

        with col2:

            st.metric(
                "Completed Exercises",
                completed_exercises,
            )

        st.divider()

        for workout in reversed(
            history
        ):

            date = workout.get(
                "date",
                "",
            )

            time = workout.get(
                "time",
                "",
            )

            workout_name = workout.get(
                "workout_name",
                "Workout",
            )

            exercises = workout.get(
                "exercises",
                [],
            )

            completed_count = sum(
                1
                for exercise in exercises
                if exercise.get(
                    "completed",
                    False,
                )
            )

            with st.expander(
                f"📅 {date} — "
                f"{workout_name} "
                f"({completed_count}/{len(exercises)} exercises)"
            ):

                if time:

                    st.write(
                        f"**Time:** {time}"
                    )

                actual_duration = (
                    workout.get(
                        "actual_duration"
                    )
                )

                if actual_duration:

                    st.write(
                        f"**Duration:** "
                        f"{actual_duration} minutes"
                    )

                total_sets = workout.get(
                    "total_sets"
                )

                if total_sets is not None:

                    st.write(
                        f"**Completed Sets:** "
                        f"{total_sets}"
                    )

                total_volume = workout.get(
                    "total_volume"
                )

                if total_volume is not None:

                    st.write(
                        f"**Total Volume:** "
                        f"{float(total_volume):,.1f} kg"
                    )

                st.divider()

                for exercise in exercises:

                    status = (
                        "✅"
                        if exercise.get(
                            "completed",
                            False,
                        )
                        else "❌"
                    )

                    st.write(
                        f"{status} "
                        f"**{exercise.get('name', 'Exercise')}**"
                    )

                    sets = exercise.get(
                        "sets",
                        [],
                    )

                    if sets:

                        for set_data in sets:

                            set_number = (
                                set_data.get(
                                    "set_number",
                                    "-",
                                )
                            )

                            set_completed = (
                                "✅"
                                if set_data.get(
                                    "completed",
                                    False,
                                )
                                else "❌"
                            )

                            weight = (
                                set_data.get(
                                    "weight_kg",
                                    0,
                                )
                            )

                            reps = (
                                set_data.get(
                                    "actual_reps",
                                    0,
                                )
                            )

                            volume = (
                                set_data.get(
                                    "volume",
                                    0,
                                )
                            )

                            st.write(
                                f"Set {set_number}: "
                                f"{set_completed} "
                                f"{weight} kg × "
                                f"{reps} reps "
                                f"— {volume:,.1f} kg volume"
                            )

                    else:

                        col1, col2, col3 = (
                            st.columns(3)
                        )

                        with col1:

                            st.write(
                                f"Planned: "
                                f"{exercise.get('planned_sets', '-')}"
                                f" × "
                                f"{exercise.get('planned_reps', '-')}"
                            )

                        with col2:

                            st.write(
                                f"Actual reps: "
                                f"{exercise.get('actual_reps', '-')}"
                            )

                        with col3:

                            st.write(
                                f"Weight: "
                                f"{exercise.get('weight_kg', 0)} kg"
                            )

                notes = workout.get(
                    "notes",
                    "",
                )

                if notes:

                    st.divider()

                    st.write(
                        f"📝 **Notes:** {notes}"
                    )


# ============================================================
# PROGRESS
# ============================================================

elif st.session_state.page == "Progress":

    st.title("📈 Progress")

    history = (
        st.session_state.workout_history
    )

    if not history:

        st.info(
            "Your progress dashboard will become "
            "more useful after you complete some workouts."
        )

        st.write(
            "Complete workouts and log your weights "
            "and reps. Your training history will "
            "automatically appear here."
        )

    else:

        total_workouts = len(
            history
        )

        workouts_this_week = (
            get_workouts_this_week(
                history
            )
        )

        workouts_this_month = (
            get_workouts_this_month(
                history
            )
        )

        total_exercises = (
            get_completed_exercises_count(
                history
            )
        )

        performance = (
            get_exercise_performance(
                history
            )
        )

        st.subheader(
            "📊 Training Overview"
        )

        col1, col2, col3, col4 = (
            st.columns(4)
        )

        with col1:

            st.metric(
                "Total Workouts",
                total_workouts,
            )

        with col2:

            st.metric(
                "This Week",
                workouts_this_week,
            )

        with col3:

            st.metric(
                "This Month",
                workouts_this_month,
            )

        with col4:

            st.metric(
                "Exercises Completed",
                total_exercises,
            )

        st.divider()

        total_volume = 0.0

        for entries in performance.values():

            for entry in entries:

                total_volume += float(
                    entry.get(
                        "volume",
                        0,
                    )
                )

        if total_volume == 0:

            for workout in history:

                total_volume += float(
                    workout.get(
                        "total_volume",
                        0,
                    )
                )

        st.subheader(
            "🏋️ Training Volume"
        )

        col1, col2 = (
            st.columns(2)
        )

        with col1:

            st.metric(
                "Total Logged Volume",
                f"{total_volume:,.1f} kg",
            )

        with col2:

            st.write(
                "Training volume is calculated as "
                "**weight × actual reps** for completed "
                "sets where weight and reps were logged."
            )

        st.divider()

        st.subheader(
            "🏆 Personal Records"
        )

        personal_records = (
            calculate_personal_records(
                performance
            )
        )

        if personal_records:

            st.write(
                "Your best recorded performances "
                "for each exercise."
            )

            st.dataframe(
                personal_records,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Complete exercises and record "
                "weights/reps to create personal records."
            )

        st.divider()

        st.subheader(
            "📈 Exercise Progression"
        )

        summaries = (
            calculate_exercise_summary(
                performance
            )
        )

        if summaries:

            st.dataframe(
                summaries,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Complete exercises and record "
                "weights/reps to build progression data."
            )

        st.divider()

        st.subheader(
            "💪 Exercise Detail"
        )

        if performance:

            exercise_names = sorted(
                performance.keys()
            )

            selected_exercise = (
                st.selectbox(
                    "Select an exercise",
                    exercise_names,
                )
            )

            exercise_history = (
                performance[
                    selected_exercise
                ]
            )

            exercise_history = sorted(
                exercise_history,
                key=lambda item: (
                    datetime.strptime(
                        item["date"],
                        "%Y-%m-%d",
                    )
                    if item.get("date")
                    else datetime.min
                ),
            )

            st.write(
                f"### {selected_exercise}"
            )

            latest = exercise_history[-1]

            best_weight = max(
                entry.get(
                    "weight_kg",
                    0,
                )
                for entry in exercise_history
            )

            best_reps = max(
                entry.get(
                    "actual_reps",
                    0,
                )
                for entry in exercise_history
            )

            exercise_volume = sum(
                entry.get(
                    "volume",
                    0,
                )
                for entry in exercise_history
            )

            col1, col2, col3, col4 = (
                st.columns(4)
            )

            with col1:

                st.metric(
                    "Latest Weight",
                    f"{latest.get('weight_kg', 0)} kg",
                )

            with col2:

                st.metric(
                    "Best Weight",
                    f"{best_weight} kg",
                )

            with col3:

                st.metric(
                    "Latest Reps",
                    latest.get(
                        "actual_reps",
                        0,
                    ),
                )

            with col4:

                st.metric(
                    "Best Reps",
                    best_reps,
                )

            progress_change = (
                get_progress_change(
                    exercise_history
                )
            )

            if progress_change:

                weight_change = (
                    progress_change[
                        "weight_change"
                    ]
                )

                percentage = (
                    progress_change[
                        "percentage"
                    ]
                )

                if percentage is not None:

                    if weight_change > 0:

                        st.success(
                            f"📈 Weight increased by "
                            f"{weight_change:.1f} kg "
                            f"({percentage:.1f}%) "
                            f"since your first logged session."
                        )

                    elif weight_change < 0:

                        st.warning(
                            f"Weight is "
                            f"{abs(weight_change):.1f} kg "
                            f"below your first logged session."
                        )

                    else:

                        st.info(
                            "Your logged weight is "
                            "unchanged from your first session."
                        )

            st.write(
                f"**Total volume for this exercise:** "
                f"{exercise_volume:,.1f} kg"
            )

            st.write(
                "### Session History"
            )

            for entry in reversed(
                exercise_history
            ):

                st.write(
                    f"**{entry.get('date', '-')}** — "
                    f"{entry.get('weight_kg', 0)} kg × "
                    f"{entry.get('actual_reps', 0)} reps "
                    f"— Volume: "
                    f"{entry.get('volume', 0):,.1f} kg"
                )

        else:

            st.info(
                "No exercise performance data is available yet."
            )


# ============================================================
# AI COACH
# ============================================================

elif st.session_state.page == "Admin: Registrations":
    st.title("Admin Dashboard")
    st.caption("Registration activity visible only to the configured administrator.")
    if not registration_admin_configured():
        st.error(
            "Admin data access is not configured. Add "
            "SUPABASE_SERVICE_ROLE_KEY to local Streamlit secrets."
        )
    try:
        events = load_registration_events()
    except Exception:
        logger.exception("Admin registration dashboard failed to load")
        events = []
        st.error(
            "Registration data could not be loaded. Check the Supabase table "
            "grants and application logs."
        )
    if events:
        st.metric("Registered users", len(events))
        st.dataframe(events, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No registered users found. Verify the service-role key belongs "
            "to this Supabase project and that Supabase Auth contains users."
        )

elif st.session_state.page == "AI Coach":

    st.title("AI Workout Coach")

    profile = st.session_state.get("profile", {})
    workout_plan = st.session_state.get("workout_plan", [])
    workout_history = st.session_state.get("workout_history", [])

    if not profile:
        st.warning("Please create your profile first.")
    else:
        st.caption(f"Active Model Layer: {GEMINI_MODEL}")
        st.write("---")
        
        # Initialize thread state data array memory
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": f"Hello {profile.get('name', 'Athlete')}! I have analyzed your workout splits and neck recovery limitations. Let\'s discuss scaling your exercises safely!"}
            ]

        # Render dialogue messages in chronological order inside native layout bubbles
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Mount a sticky bottom chat input bubble layer block cell text row hook
        if user_query := st.chat_input("Ask a follow-up about your exercise targets or neck limits..."):
            
            # Render user query instantly on screen canvas canvas elements
            with st.chat_message("user"):
                st.markdown(user_query)
                
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            
            # Combine history array strings into a contextual prompt for Gemini
            prompt_builder = []
            for item in st.session_state.chat_history[-5:]:
                prefix = "User: " if item["role"] == "user" else "Coach: "
                prompt_builder.append(f"{prefix}{item['content']}")
                
            combined_context_query = "\n".join(prompt_builder) + "\n\nProvide your next direct answer back as the AI coach matching this dialogue history context."
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        coach_response = ask_ai_coach(
                            combined_context_query,
                            profile,
                            workout_plan,
                            workout_history,
                        )
                        st.markdown(coach_response)
                        st.session_state.chat_history.append({"role": "assistant", "content": coach_response})
                    except Exception as e:
                        st.error(f"Failed to compile response item logic: {str(e)}")
            # No st.rerun() needed: the inline render + session_state already
            # persist the new messages and the page correctly shows the chat bubbles above.
            # forcing a rerun would only wastes a full app re-execution for no UX
            # benefit since chat_history is already in session_state