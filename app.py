import modules.auth as auth
from infrastructure.storage import reset_user_progress_soft

import json
from datetime import datetime

import streamlit as st

from application.data_loader import load_persistent_data as _load_persistent_data
from config.settings import DATA_DIR
from presentation.session_state import initialize_session_state

# Streamlit page configuration must be the first Streamlit command.
st.set_page_config(
    page_title="Personal Workout Trainer",
    page_icon="🏋️‍♂️",
    layout="wide",
)

# ============================================================
# MASTER PRODUCTION AKHADA SAFFRON THEME INJECTION
# ============================================================
st.markdown("""
<style>
    /* Force midnight canvas background matching the sidebar */
    .stApp, div[data-testid="stAppViewContainer"], .main, [data-testid="stMainSpaceContainer"] {
        background-color: #171B26 !important;
        background: #171B26 !important;
    }
    
    /* Enforce high-visibility white typography cross-cohesion */
    h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown {
        color: #FFFFFF !important;
    }
    
    /* Elegant Saffron Highlights for your metric numbers */
    div[data-testid="stMetricValue"] {
        color: #FF6B00 !important;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
    }

    /* Core logging frames */
    input, select, textarea, div[data-baseweb="input"], .stNumberInput input {
        background-color: #222533 !important;
        color: #FFFFFF !important;
        border: 1px solid #33384F !important;
    }
</style>
""", unsafe_allow_html=True)


from modules.workout_generator import (
    normalize_workout_plan,
    generate_weekly_plan,
)
from domain.workout_validation import has_duplicate_exercises

from domain.exercise_rules import (
    get_completed_exercises_count,
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

st.markdown("""
        <style>
            /* Dynamic Bodyweight UI Rule: When an input card possesses a zero placeholder value, fade the weight cell container visually */
            div[data-testid="stMarkdownContainer"] p:contains("Weight") + div input[value="0.0"],
            div[data-testid="stNumberInput"]-ext-disabled {
                opacity: 0.25;
                pointer-events: none;
            }
        </style>
    """, unsafe_allow_html=True)


# Secure User Multi-Tenant Gatekeeper
if "user" not in st.session_state:
    auth.render_login_interface()
    st.markdown("<style>[data-testid='stSidebarNav'] {display: none;} div.block-container {padding-top: 2rem;}</style>", unsafe_allow_html=True)
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
    get_best_strength_highlights,
    get_completed_workouts_this_week,
    get_next_workout,
    get_recent_workouts,
    get_week_start,
    get_workout_date,
    safe_float,
    safe_int,
)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.title(
    "🏋️ Personal Workout Trainer"
)

page_options = [
    "Dashboard",
    "My Profile",
    "My Workout",
    "Workout History",
    "Progress",
    "AI Coach",
]

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
    st.session_state.clear()
    st.success("Session disconnected successfully! Clearing active arrays...")
    st.rerun()
with st.sidebar.expander("Danger Zone 🚨", expanded=False):
    st.write("Wipe existing test logs to clear room for your true tracking data.")
    if st.button("Reset Progress & Start Fresh", type="primary", use_container_width=True):
        pass
        
        with st.spinner("Purging test data..."):
            if reset_user_progress_soft():
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
            "Welcome to your Personal Workout Trainer!"
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

        st.subheader(
            f"Welcome back, {name}! 👋"
        )

        st.caption(
            f"Goal: **{fitness_goal}** • "
            f"Level: **{fitness_level}**"
        )

        st.divider()

        total_workouts = len(
            workout_history
        )

        workouts_this_week = (
            get_completed_workouts_this_week(
                workout_history
            )
        )

        current_streak = (
            calculate_current_streak(
                workout_history
            )
        )

        total_volume = (
            calculate_total_volume(
                workout_history
            )
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

        for workout_day in workout_plan:

            day_number = workout_day.get(
                "day",
                "",
            )

            day_name = workout_day.get(
                "name",
                "Workout",
            )

            duration = workout_day.get(
                "duration",
                45,
            )

            intensity = workout_day.get(
                "intensity",
                "Moderate",
            )

            warmup = workout_day.get(
                "warmup",
                "5-10 minutes",
            )

            exercises = workout_day.get(
                "exercises",
                [],
            )

            with st.expander(
                f"Day {day_number}: {day_name}",
                expanded=False,
            ):

                col1, col2, col3 = (
                    st.columns(3)
                )

                with col1:

                    st.metric(
                        "Duration",
                        f"{duration} min",
                    )

                with col2:

                    st.metric(
                        "Intensity",
                        intensity,
                    )

                with col3:

                    st.metric(
                        "Exercises",
                        len(exercises),
                    )

                st.write(
                    f"🔥 **Warm-up:** {warmup}"
                )

                for index, exercise in enumerate(
                    exercises,
                    start=1,
                ):

                    st.markdown(
                        f"### {index}. "
                        f"{exercise.get('name', 'Exercise')}"
                    )

                    col1, col2, col3, col4 = (
                        st.columns(4)
                    )

                    with col1:

                        st.write(
                            f"**Sets:** "
                            f"{exercise.get('sets', '-')}"
                        )

                    with col2:

                        st.write(
                            f"**Reps:** "
                            f"{exercise.get('reps', '-')}"
                        )

                    with col3:

                        st.write(
                            f"**Rest:** "
                            f"{exercise.get('rest', '-')}"
                        )

                    with col4:

                        st.write(
                            f"**Equipment:** "
                            f"{exercise.get('equipment', '-')}"
                        )

                    st.write(
                        f"**Primary Muscle:** "
                        f"{exercise.get('primary_muscle', '-')}"
                    )

                    st.write(
                        f"**Movement:** "
                        f"{exercise.get('movement_pattern', '-')}"
                    )

                    instructions = (
                        exercise.get(
                            "instructions",
                            "",
                        )
                    )

                    if instructions:

                        with st.expander(
                            "How to perform"
                        ):

                            st.write(
                                instructions
                            )

                st.write(
                    f"🧘 **Cooldown:** "
                    f"{workout_day.get('cooldown', '5 minutes')}"
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
            st.rerun()