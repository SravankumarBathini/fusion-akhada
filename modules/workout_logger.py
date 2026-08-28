import json
from datetime import datetime
from pathlib import Path

import streamlit as st


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_reps(reps_value):
    """
    Convert planned reps such as:
    8
    "8"
    "8-10"
    "5–8"
    into a sensible default integer.
    """
    if isinstance(reps_value, int):
        return reps_value

    if isinstance(reps_value, float):
        return int(reps_value)

    if not reps_value:
        return 8

    text = str(reps_value).strip()

    for separator in ("-", "–", "—", "to"):
        if separator in text:
            first = text.split(separator)[0].strip()
            try:
                return int(float(first))
            except ValueError:
                pass

    try:
        return int(float(text))
    except ValueError:
        return 8


def _get_planned_sets(exercise):
    return _safe_int(
        exercise.get("sets", exercise.get("planned_sets", 3)),
        3,
    )


def _get_planned_reps(exercise):
    return _parse_reps(
        exercise.get(
            "reps",
            exercise.get("planned_reps", 8),
        )
    )


def _calculate_set_volume(weight, reps):
    return round(
        _safe_float(weight) * _safe_int(reps),
        2,
    )


def _calculate_workout_totals(session):
    total_sets = 0
    total_volume = 0.0
    completed_exercises = 0

    for exercise in session.get("exercises", []):
        exercise_completed = False

        for set_data in exercise.get("sets", []):
            if set_data.get("completed", False):
                total_sets += 1

                weight = _safe_float(
                    set_data.get("weight_kg", 0)
                )

                reps = _safe_int(
                    set_data.get("actual_reps", 0)
                )

                total_volume += _calculate_set_volume(
                    weight,
                    reps,
                )

                exercise_completed = True

        if exercise_completed:
            completed_exercises += 1

    return (
        total_sets,
        round(total_volume, 2),
        completed_exercises,
    )


def _load_history(history_file):
    path = Path(history_file)

    try:
        if path.exists():
            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

                if isinstance(data, list):
                    return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return []


def _save_history(history_file, history, save_json_function):
    save_json_function(
        history_file,
        history,
    )


# ============================================================
# PREVIOUS PERFORMANCE
# ============================================================

def _get_previous_performance(
    workout_history,
    exercise_name,
):
    """
    Find the most recent logged performance
    for an exercise.
    """

    for workout in reversed(workout_history):
        for exercise in workout.get("exercises", []):

            if (
                exercise.get("name", "").strip().lower()
                == exercise_name.strip().lower()
            ):

                sets = exercise.get("sets", [])

                completed_sets = [
                    item
                    for item in sets
                    if item.get("completed", False)
                ]

                if completed_sets:

                    last_set = completed_sets[-1]

                    return {
                        "weight_kg": last_set.get(
                            "weight_kg",
                            0,
                        ),
                        "actual_reps": last_set.get(
                            "actual_reps",
                            0,
                        ),
                    }

    return None


# ============================================================
# SESSION INITIALIZATION
# ============================================================

def _initialize_session(workout_plan):
    """
    Create a fresh active workout session.
    """

    exercises = []

    for exercise in workout_plan.get("exercises", []):

        planned_sets = _get_planned_sets(
            exercise
        )

        planned_reps = _get_planned_reps(
            exercise
        )

        sets = []

        for set_number in range(
            1,
            planned_sets + 1,
        ):
            sets.append(
                {
                    "set_number": set_number,
                    "weight_kg": 0.0,
                    "actual_reps": 0,
                    "completed": False,
                    "volume": 0.0,
                }
            )

        exercises.append(
            {
                "name": exercise.get(
                    "name",
                    "Exercise",
                ),
                "planned_sets": planned_sets,
                "planned_reps": planned_reps,
                "equipment": exercise.get(
                    "equipment",
                    "",
                ),
                "primary_muscle": exercise.get(
                    "primary_muscle",
                    "",
                ),
                "sets": sets,
                "completed": False,
            }
        )

    return {
        "started_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "exercises": exercises,
        "notes": "",
    }


# ============================================================
# SESSION STATE
# ============================================================

def _ensure_session_state():

    if "active_workout_session" not in st.session_state:
        st.session_state.active_workout_session = None

    if "workout_session_started" not in st.session_state:
        st.session_state.workout_session_started = False

    if "selected_workout_day" not in st.session_state:
        st.session_state.selected_workout_day = 0


# ============================================================
# RENDER LOGGER
# ============================================================

def render_workout_logger(
    workout_plan,
    workout_history,
    history_file,
    save_json_function,
):

    _ensure_session_state()

    if not workout_plan:
        st.info(
            "Generate a workout plan first."
        )
        return

    # ========================================================
    # SESSION MODE
    # ========================================================

    if not st.session_state.workout_session_started:

        st.subheader(
            "🚀 Start Today's Workout"
        )

        day_names = []

        for index, workout_day in enumerate(
            workout_plan
        ):
            day_number = workout_day.get(
                "day",
                index + 1,
            )

            day_name = workout_day.get(
                "name",
                f"Workout Day {day_number}",
            )

            day_names.append(
                f"Day {day_number}: {day_name}"
            )

        selected_day = st.selectbox(
            "Choose workout",
            range(len(day_names)),
            format_func=lambda index: day_names[index],
            key="workout_day_selector",
        )

        selected_workout = workout_plan[
            selected_day
        ]

        exercises = selected_workout.get(
            "exercises",
            [],
        )

        st.write(
            f"**{selected_workout.get('name', 'Workout')}**"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Duration",
                f"{selected_workout.get('duration', 45)} min",
            )

        with col2:
            st.metric(
                "Exercises",
                len(exercises),
            )

        with col3:
            st.metric(
                "Intensity",
                selected_workout.get(
                    "intensity",
                    "Moderate",
                ),
            )

        if exercises:

            st.write(
                "### Today's Exercises"
            )

            for index, exercise in enumerate(
                exercises,
                start=1,
            ):

                st.write(
                    f"{index}. "
                    f"**{exercise.get('name', 'Exercise')}** — "
                    f"{exercise.get('sets', '-')} × "
                    f"{exercise.get('reps', '-')}"
                )

            st.divider()

            if st.button(
                "▶️ Start Workout",
                type="primary",
                use_container_width=True,
            ):

                st.session_state.active_workout_session = (
                    _initialize_session(
                        selected_workout
                    )
                )

                st.session_state.selected_workout_day = (
                    selected_day
                )

                st.session_state.workout_session_started = (
                    True
                )

                st.rerun()

        return

    # ========================================================
    # ACTIVE WORKOUT
    # ========================================================

    session = (
        st.session_state.active_workout_session
    )

    if not session:
        st.session_state.workout_session_started = False
        st.rerun()
        return

    selected_day = (
        st.session_state.selected_workout_day
    )

    selected_workout = workout_plan[
        selected_day
    ]

    st.subheader(
        "🏋️ Workout in Progress"
    )

    started_at = session.get(
        "started_at",
        "",
    )

    if started_at:
        try:
            started = datetime.fromisoformat(
                started_at
            )

            elapsed = (
                datetime.now() - started
            ).total_seconds() / 60

            st.caption(
                f"⏱️ Workout started at "
                f"{started.strftime('%H:%M')} "
                f"• Approximately "
                f"{int(elapsed)} minutes elapsed"
            )

        except ValueError:
            pass

    total_sets, total_volume, completed_exercises = (
        _calculate_workout_totals(session)
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Exercises Completed",
            completed_exercises,
        )

    with col2:
        st.metric(
            "Sets Completed",
            total_sets,
        )

    with col3:
        st.metric(
            "Volume",
            f"{total_volume:,.1f} kg",
        )

    st.divider()

    # ========================================================
    # EXERCISES
    # ========================================================

    for exercise_index, exercise in enumerate(
        session.get("exercises", [])
    ):

        exercise_name = exercise.get(
            "name",
            "Exercise",
        )

        planned_sets = exercise.get(
            "planned_sets",
            3,
        )

        planned_reps = exercise.get(
            "planned_reps",
            8,
        )

        previous = _get_previous_performance(
            workout_history,
            exercise_name,
        )

        completed_sets = sum(
            1
            for set_data in exercise.get(
                "sets",
                [],
            )
            if set_data.get(
                "completed",
                False,
            )
        )

        with st.expander(
            f"{'✅' if exercise.get('completed') else '⬜'} "
            f"{exercise_name} "
            f"({completed_sets}/{planned_sets} sets)",
            expanded=True,
        ):

            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(
                    f"**Planned:** "
                    f"{planned_sets} × {planned_reps}"
                )

            with col2:

                if previous:
                    st.write(
                        f"**Previous:** "
                        f"{previous.get('weight_kg', 0)} kg × "
                        f"{previous.get('actual_reps', 0)}"
                    )
                else:
                    st.write(
                        "**Previous:** No data"
                    )

            with col3:
                st.write(
                    f"**Equipment:** "
                    f"{exercise.get('equipment', '-')}"
                )

            st.divider()

            # ------------------------------------------------
            # SET LOGGER
            # ------------------------------------------------

            for set_index, set_data in enumerate(
                exercise.get("sets", [])
            ):

                set_number = set_index + 1

                col1, col2, col3, col4 = (
                    st.columns(
                        [0.8, 1.4, 1.4, 1]
                    )
                )

                with col1:
                    st.write(
                        f"**Set {set_number}**"
                    )

                with col2:

                    weight = st.number_input(
                        "Weight (kg)",
                        min_value=0.0,
                        max_value=500.0,
                        value=float(
                            set_data.get(
                                "weight_kg",
                                0.0,
                            )
                        ),
                        step=0.5,
                        key=(
                            f"weight_"
                            f"{exercise_index}_"
                            f"{set_index}"
                        ),
                    )

                with col3:

                    reps = st.number_input(
                        "Reps",
                        min_value=0,
                        max_value=200,
                        value=int(
                            set_data.get(
                                "actual_reps",
                                0,
                            )
                        ),
                        step=1,
                        key=(
                            f"reps_"
                            f"{exercise_index}_"
                            f"{set_index}"
                        ),
                    )

                with col4:

                    completed = st.checkbox(
                        "Done",
                        value=set_data.get(
                            "completed",
                            False,
                        ),
                        key=(
                            f"done_"
                            f"{exercise_index}_"
                            f"{set_index}"
                        ),
                    )

                set_data["weight_kg"] = weight
                set_data["actual_reps"] = reps
                set_data["completed"] = completed

                set_data["volume"] = (
                    _calculate_set_volume(
                        weight,
                        reps,
                    )
                    if completed
                    else 0.0
                )

            # ------------------------------------------------
            # EXERCISE COMPLETE
            # ------------------------------------------------

            all_completed = (
                completed_sets >= planned_sets
                and planned_sets > 0
            )

            exercise["completed"] = all_completed

            if all_completed:
                st.success(
                    "Exercise completed! ✅"
                )

    st.divider()

    # ========================================================
    # NOTES
    # ========================================================

    st.subheader(
        "📝 Workout Notes"
    )

    session["notes"] = st.text_area(
        "How did the workout feel?",
        value=session.get(
            "notes",
            "",
        ),
        placeholder=(
            "Example: Felt strong today. "
            "Bench press was difficult on the final set."
        ),
        height=100,
        key="active_workout_notes",
    )

    st.divider()

    # ========================================================
    # ACTION BUTTONS
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "💾 Save Progress",
            use_container_width=True,
        ):

            st.session_state.active_workout_session = (
                session
            )

            st.success(
                "Current workout progress is saved in this session."
            )

    with col2:

        if st.button(
            "🏁 Finish Workout",
            type="primary",
            use_container_width=True,
        ):

            total_sets, total_volume, completed_exercises = (
                _calculate_workout_totals(
                    session
                )
            )

            completed_at = datetime.now()

            started_at = session.get(
                "started_at"
            )

            actual_duration = None

            if started_at:

                try:

                    start_time = datetime.fromisoformat(
                        started_at
                    )

                    actual_duration = max(
                        1,
                        int(
                            (
                                completed_at
                                - start_time
                            ).total_seconds()
                            / 60
                        ),
                    )

                except ValueError:
                    pass

            completed_workout = {
                "date": completed_at.strftime(
                    "%Y-%m-%d"
                ),
                "time": completed_at.strftime(
                    "%H:%M:%S"
                ),
                "workout_name": selected_workout.get(
                    "name",
                    "Workout",
                ),
                "planned_duration": selected_workout.get(
                    "duration",
                    45,
                ),
                "actual_duration": actual_duration,
                "total_sets": total_sets,
                "total_volume": total_volume,
                "completed_exercises": completed_exercises,
                "notes": session.get(
                    "notes",
                    "",
                ),
                "exercises": session.get(
                    "exercises",
                    [],
                ),
            }

            history = _load_history(
                history_file
            )

            history.append(
                completed_workout
            )

            _save_history(
                history_file,
                history,
                save_json_function,
            )

            st.session_state.workout_history = (
                history
            )

            # Clear active session
            st.session_state.active_workout_session = None
            st.session_state.workout_session_started = False

            st.success(
                "🎉 Workout completed and saved!"
            )

            st.balloons()

            # ------------------------------------------------
            # COMPLETION SUMMARY
            # ------------------------------------------------

            st.subheader(
                "📊 Workout Summary"
            )

            col1, col2, col3, col4 = (
                st.columns(4)
            )

            with col1:
                st.metric(
                    "Exercises",
                    completed_exercises,
                )

            with col2:
                st.metric(
                    "Sets",
                    total_sets,
                )

            with col3:
                st.metric(
                    "Volume",
                    f"{total_volume:,.1f} kg",
                )

            with col4:
                st.metric(
                    "Duration",
                    (
                        f"{actual_duration} min"
                        if actual_duration
                        else "-"
                    ),
                )

            st.info(
                "Your workout has been added to Workout History "
                "and will be used by Progress and AI Coach."
            )

            st.rerun()

    st.divider()

    # ========================================================
    # CANCEL WORKOUT
    # ========================================================

    if st.button(
        "Cancel Active Workout",
        type="secondary",
    ):

        st.session_state.active_workout_session = None
        st.session_state.workout_session_started = False

        st.warning(
            "Active workout cancelled. "
            "No workout was added to history."
        )

        st.rerun()