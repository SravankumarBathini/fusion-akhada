from utils.storage import reset_user_progress_soft

import json
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from modules.workout_generator import (
    normalize_workout_plan,
    generate_weekly_plan,
)

from modules.analytics import (
    get_completed_exercises_count,
    get_workouts_this_week,
    get_workouts_this_month,
    get_exercise_performance,
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

from utils.storage import (
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

st.set_page_config(
    page_title="Personal Workout Trainer",
    page_icon="🏋️",
    layout="wide",
)


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

PROFILE_FILE = DATA_DIR / "profile.json"
WORKOUT_PLAN_FILE = DATA_DIR / "workout_plan.json"
WORKOUT_HISTORY_FILE = DATA_DIR / "workout_history.json"
EXERCISES_FILE = DATA_DIR / "exercises.json"


# ============================================================
# SESSION STATE
# ============================================================

if "profile_created" not in st.session_state:
    st.session_state.profile_created = False

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "workout_plan" not in st.session_state:
    st.session_state.workout_plan = []

if "workout_history" not in st.session_state:
    st.session_state.workout_history = []

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "cloud_data_loaded" not in st.session_state:
    st.session_state.cloud_data_loaded = False

if "profile_id" not in st.session_state:
    st.session_state.profile_id = None

if "storage_source" not in st.session_state:
    st.session_state.storage_source = "local"


# ============================================================
# PERSISTENT DATA LOADING
# ============================================================

def load_persistent_data():
    """
    Load application data.

    Priority:

    1. Supabase
    2. Local JSON fallback

    Exercises remain local because they are static reference data.
    """

    # --------------------------------------------------------
    # LOCAL REFERENCE DATA
    # --------------------------------------------------------

    exercise_database = load_json(
        EXERCISES_FILE,
        [],
    )

    # --------------------------------------------------------
    # SUPABASE
    # --------------------------------------------------------

    if is_supabase_available():

        try:

            profile = load_latest_profile_from_supabase()

            if profile:

                profile_id = get_latest_profile_id()

                workout_plan = []

                if profile_id:

                    cloud_plan = (
                        load_latest_workout_plan_from_supabase(
                            profile_id
                        )
                    )

                    if cloud_plan:
                        workout_plan = cloud_plan

                # ------------------------------------------------
                # WORKOUT HISTORY FROM SUPABASE
                # ------------------------------------------------

                workout_history = []

                if profile_id:

                    workout_history = (
                        load_workout_history_from_supabase(
                            profile_id
                        )
                    )

                return (
                    profile,
                    workout_plan,
                    workout_history,
                    exercise_database,
                    profile_id,
                    "supabase",
                )

        except Exception as error:

            st.warning(
                "Supabase is configured, but cloud data could "
                f"not be loaded. Using local data instead. "
                f"Details: {error}"
            )

    # --------------------------------------------------------
    # LOCAL FALLBACK
    # --------------------------------------------------------

    profile = load_json(
        PROFILE_FILE,
        {},
    )

    workout_plan = load_json(
        WORKOUT_PLAN_FILE,
        [],
    )

    workout_history = load_json(
        WORKOUT_HISTORY_FILE,
        [],
    )

    return (
        profile,
        workout_plan,
        workout_history,
        exercise_database,
        None,
        "local",
    )


# ============================================================
# LOAD DATA ONCE PER SESSION
# ============================================================

if not st.session_state.cloud_data_loaded:

    (
        loaded_profile,
        loaded_workout_plan,
        loaded_workout_history,
        exercise_database,
        loaded_profile_id,
        storage_source,
    ) = load_persistent_data()

    st.session_state.profile = (
        loaded_profile or {}
    )

    st.session_state.profile_created = bool(
        loaded_profile
    )

    st.session_state.workout_plan = (
        loaded_workout_plan or []
    )

    st.session_state.workout_history = (
        loaded_workout_history or []
    )

    st.session_state.profile_id = (
        loaded_profile_id
    )

    st.session_state.storage_source = (
        storage_source
    )

    st.session_state.cloud_data_loaded = True

else:

    exercise_database = load_json(
        EXERCISES_FILE,
        [],
    )


# ============================================================
# NORMALIZE WORKOUT PLAN
# ============================================================

st.session_state.workout_plan = normalize_workout_plan(
    st.session_state.workout_plan
)


# ============================================================
# DASHBOARD HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_workout_date(workout):
    date_value = workout.get(
        "date",
        "",
    )

    if not date_value:
        return None

    try:

        return datetime.strptime(
            str(date_value),
            "%Y-%m-%d",
        ).date()

    except (
        TypeError,
        ValueError,
    ):
        return None


def calculate_total_volume(history):
    total_volume = 0.0

    for workout in history:

        workout_volume = safe_float(
            workout.get(
                "total_volume",
                0,
            )
        )

        if workout_volume:

            total_volume += workout_volume

            continue

        exercises = workout.get(
            "exercises",
            [],
        )

        for exercise in exercises:

            sets = exercise.get(
                "sets",
                [],
            )

            for set_data in sets:

                if not set_data.get(
                    "completed",
                    False,
                ):
                    continue

                weight = safe_float(
                    set_data.get(
                        "weight_kg",
                        0,
                    )
                )

                reps = safe_int(
                    set_data.get(
                        "actual_reps",
                        0,
                    )
                )

                total_volume += (
                    weight * reps
                )

    return total_volume


def calculate_current_streak(history):
    completed_dates = set()

    for workout in history:

        date_value = get_workout_date(
            workout
        )

        if date_value:
            completed_dates.add(
                date_value
            )

    if not completed_dates:
        return 0

    today = datetime.now().date()

    if today in completed_dates:

        current_date = today

    elif (
        today - timedelta(days=1)
        in completed_dates
    ):

        current_date = (
            today - timedelta(days=1)
        )

    else:

        return 0

    streak = 0

    while current_date in completed_dates:

        streak += 1

        current_date -= timedelta(
            days=1
        )

    return streak


def get_week_start():

    today = datetime.now().date()

    return today - timedelta(
        days=today.weekday()
    )


def get_completed_workouts_this_week(
    history
):

    week_start = get_week_start()

    today = datetime.now().date()

    count = 0

    for workout in history:

        date_value = get_workout_date(
            workout
        )

        if (
            date_value
            and week_start
            <= date_value
            <= today
        ):

            count += 1

    return count


def get_next_workout(
    workout_plan,
    history,
):

    if not workout_plan:
        return None

    today = datetime.now().date()

    weekday = today.weekday()

    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    today_name = weekday_names[
        weekday
    ]

    for workout in workout_plan:

        day_of_week = str(
            workout.get(
                "day_of_week",
                "",
            )
        ).strip()

        if (
            day_of_week.lower()
            == today_name.lower()
        ):

            return workout

    for workout in workout_plan:

        day_value = workout.get(
            "day"
        )

        if safe_int(
            day_value,
            -1,
        ) == weekday + 1:

            return workout

    if workout_plan:

        index = (
            weekday
            % len(workout_plan)
        )

        return workout_plan[index]

    return None


def get_recent_workouts(
    history,
    limit=3,
):

    valid_workouts = [
        workout
        for workout in history
        if get_workout_date(workout)
        is not None
    ]

    valid_workouts.sort(
        key=lambda workout:
        get_workout_date(workout),
        reverse=True,
    )

    return valid_workouts[:limit]


def get_best_strength_highlights(
    history
):

    performance = (
        get_exercise_performance(
            history
        )
    )

    highlights = []

    for (
        exercise_name,
        entries,
    ) in performance.items():

        if not entries:
            continue

        best_entry = max(
            entries,
            key=lambda entry: (
                safe_float(
                    entry.get(
                        "weight_kg",
                        0,
                    )
                ),
                safe_int(
                    entry.get(
                        "actual_reps",
                        0,
                    )
                ),
            ),
        )

        weight = safe_float(
            best_entry.get(
                "weight_kg",
                0,
            )
        )

        reps = safe_int(
            best_entry.get(
                "actual_reps",
                0,
            )
        )

        if weight > 0 and reps > 0:

            highlights.append(
                {
                    "exercise": exercise_name,
                    "weight": weight,
                    "reps": reps,
                    "date": best_entry.get(
                        "date",
                        "",
                    ),
                }
            )

    highlights.sort(
        key=lambda item: (
            item["weight"],
            item["reps"],
        ),
        reverse=True,
    )

    return highlights[:5]


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

    st.sidebar.info(
        "💾 Storage: Local JSON"
    )




# ============================================================
# DANGER ZONE: DATA CLEANUP CONTROLLER
# ============================================================
st.sidebar.markdown("---")
with st.sidebar.expander("Danger Zone 🚨", expanded=False):
    st.write("Wipe existing test logs to clear room for your true tracking data.")
    if st.button("Reset Progress & Start Fresh", type="primary", use_container_width=True):
        pass
        
        with st.spinner("Purging test data..."):
            if reset_user_progress_soft():
                # Instantly strip volatile states in active session memory
                st.session_state.workout_plan = []
                st.session_state.workout_history = []
                st.session_state.cloud_data_loaded = False
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

        if next_workout:

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

                if (
                    profile_id
                    and is_supabase_available()
                ):

                    save_workout_plan_to_supabase(
                        profile_id,
                        new_plan,
                    )

                else:

                    save_json(
                        WORKOUT_PLAN_FILE,
                        new_plan,
                    )

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
        }

        try:

            if is_supabase_available():

                saved_row = (
                    save_profile_to_supabase(
                        updated_profile
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

                save_json(
                    PROFILE_FILE,
                    updated_profile,
                )

                st.session_state.storage_source = (
                    "local"
                )

            st.session_state.profile = (
                updated_profile
            )

            st.session_state.profile_created = (
                True
            )

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

                if (
                    profile_id
                    and is_supabase_available()
                ):

                    save_workout_plan_to_supabase(
                        profile_id,
                        new_plan,
                    )

                else:

                    save_json(
                        WORKOUT_PLAN_FILE,
                        new_plan,
                    )

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

                if (
                    profile_id
                    and is_supabase_available()
                ):

                    save_workout_plan_to_supabase(
                        profile_id,
                        new_plan,
                    )

                else:

                    save_json(
                        WORKOUT_PLAN_FILE,
                        new_plan,
                    )

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

    st.title("🤖 AI Workout Coach")

    profile = (
        st.session_state.profile
    )

    workout_plan = (
        st.session_state.workout_plan
    )

    workout_history = (
        st.session_state.workout_history
    )

    if not profile:

        st.warning(
            "Please create your profile first."
        )

    else:

        st.write(
            "Ask your AI coach about your workouts, "
            "exercises, progression, recovery, or training."
        )

        st.caption(
            f"🟢 Gemini AI: {GEMINI_MODEL}"
        )

        question = st.text_area(
            "What would you like to ask?",
            placeholder=(
                "Example: How should I progress my bench press "
                "over the next few weeks?"
            ),
            height=120,
        )

        if st.button(
            "Ask AI Coach 🤖",
            type="primary",
        ):

            if not question.strip():

                st.warning(
                    "Please enter a question first."
                )

            else:

                with st.spinner(
                    "Your Gemini AI coach is thinking..."
                ):

                    try:

                        answer = ask_ai_coach(
                            question,
                            profile,
                            workout_plan,
                            workout_history,
                        )

                        st.subheader(
                            "Coach's Answer"
                        )

                        st.markdown(
                            answer
                        )

                    except Exception as error:

                        st.error(
                            "The AI coach could not respond."
                        )

                        st.caption(
                            f"Error: {error}"
                        )