import json
import time
import modules.ai_coach as ai_coach
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    from application.data_loader import bust_user_cache
except ImportError:  # Safe to skip cache busts in tests / headless env
    bust_user_cache = None

from domain.performance import get_progression_target
from domain.exercise_substitution import get_exercise_substitutions
from domain.exercise_rules import (
    get_exercise_instruction,
    get_exercise_coaching,
)


def _fragment_if_available(fn):
    """Apply ``@st.fragment`` when available; fall back to no-op in tests.

    ``streamlit.fragment`` was introduced in 1.37. The app runs on 1.62 so the
    decorator always applies at runtime. In unit tests (no Streamlit runtime)
    this wrapper returns ``fn`` unchanged so the logger module imports cleanly.
    """
    try:
        import streamlit as _st
        fragment_decorator = _st.fragment
    except Exception:  # pragma: no cover - test-only path
        return fn
    return fragment_decorator(fn)


def _render_set_logger(exercise_index, exercise, target_weight, target_reps):
    """Render the sets grid for one exercise using ``st.data_editor``.

    Previously each set rendered **4 separate widgets** (Set label,
    Weight number_input, Reps number_input, Done checkbox) → 4 widgets
    × 3 sets × 15 exercises = ~180 widgets that each triggered their
    own Streamlit rerun on the tiniest interaction (1 keystroke of
    weight, 1 checkbox click, etc.).

    ``st.data_editor`` collapses all sets for one exercise into a SINGLE
    widget commit model: the user edits N cells and the editor only
    notifies Streamlit ONCE when they press Enter / blur the grid.
    Inside our ``@st.fragment`` wrapper this is the difference between
    3-6 partial fragment reruns per exercise vs 30-60 tiny reruns while entering a
    full exercise — a significant chunk of the remaining "why does typing weight
    still feel laggy" tail latency.
    """
    exercise_name = exercise.get("name", "")
    ex_name_lower = exercise_name.lower()
    ex_eq_lower = str(exercise.get("equipment", "")).lower()
    is_bodyweight = any(
        kw in ex_name_lower or kw in ex_eq_lower
        for kw in [
            "bodyweight",
            "push-up",
            "pull-up",
            "plank",
            "dip",
            "chin-up",
            "crunch",
            "sit-up",
            "air squat",
            "no equipment",
        ]
    )

    sets = exercise.get("sets", [])
    if not isinstance(sets, list) or not sets:
        return

    planned_sets = len(sets)

    # ---- Build the pandas DataFrame grid from the current session sets.
    rows: list[dict[str, Any]] = []
    for set_index, set_data in enumerate(sets):
        set_number = set_index + 1
        if is_bodyweight:
            displayed_weight = 0.0
        else:
            displayed_weight = float(set_data.get("weight_kg", 0.0) or 0.0)
        rows.append(
            {
                "Set": set_number,
                "Weight (kg)": displayed_weight,
                "Target W (kg)": float(target_weight) if target_weight > 0.0 else None,
                "Reps": int(set_data.get("actual_reps", 0)) or 0,
                "Target Reps": int(target_reps) if target_weight > 0.0 else None,
                "Done": bool(set_data.get("completed", False)),
                "_set_index": set_index,
            }
        )

    df = pd.DataFrame(rows)

    # ---- Configure column behaviour.
    column_config = {
        "_set_index": None,  # hidden key column
        "Set": st.column_config.NumberColumn(
            "Set",
            disabled=True,
            min_value=1,
            max_value=planned_sets,
            step=1,
        ),
        "Weight (kg)": st.column_config.NumberColumn(
            "Weight (kg)"
            + (f" • Target {target_weight:.1f}" if target_weight > 0.0 and not is_bodyweight else ""),
            disabled=is_bodyweight,
            min_value=0.0,
            max_value=500.0,
            step=0.5,
            format="%.1f",
        ) if not is_bodyweight else st.column_config.NumberColumn(
            "Weight (kg) • Bodyweight (locked)",
            disabled=True,
            min_value=0.0,
            max_value=0.0,
            step=0.5,
            format="%.1f",
        ),
        "Target W (kg)": st.column_config.NumberColumn(
            "Target W (kg)",
            disabled=True,
            step=0.5,
            format="%.1f",
            required=False,
        ),
        "Reps": st.column_config.NumberColumn(
            "Reps" + (f" • Target {target_reps}" if target_weight > 0.0 else ""),
            min_value=0,
            max_value=200,
            step=1,
        ),
        "Target Reps": st.column_config.NumberColumn(
            "Target Reps",
            disabled=True,
            step=1,
            required=False,
        ),
        "Done": st.column_config.CheckboxColumn(
            "Done",
        ),
    }

    editor_key = f"sets_editor_{exercise_index}"

    edited_df = st.data_editor(
        df,
        key=editor_key,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config=column_config,
        column_order=(
            "Set",
            "Weight (kg)",
            "Target W (kg)",
            "Reps",
            "Target Reps",
            "Done",
        ),
    )

    # ---- Commit the edited DataFrame back into session (in-place mutation so
    #      callers (``_render_exercises_fragment``) see updated sets via the
    #      same ``exercise.get("sets")`` object they passed in.
    new_sets: list[dict[str, Any]] = []
    for _, row in edited_df.iterrows():
        try:
            set_index = int(row["_set_index"])
        except (ValueError, TypeError, KeyError):
            continue
        if 0 <= set_index < len(sets):
            set_data = sets[set_index]
        else:
            continue

        try:
            weight = float(row.get("Weight (kg)", 0.0) or 0.0)
        except (ValueError, TypeError):
            weight = 0.0
        try:
            reps = int(row.get("Reps", 0) or 0)
        except (ValueError, TypeError):
            reps = 0
        completed = bool(row.get("Done", False))

        set_data["weight_kg"] = 0.0 if is_bodyweight else weight
        set_data["actual_reps"] = reps
        set_data["completed"] = completed
        set_data["volume"] = (
            _calculate_set_volume(set_data["weight_kg"], reps) if completed else 0.0
        )
        new_sets.append(set_data)
    exercise["sets"] = new_sets


@_fragment_if_available
def _render_exercises_fragment(session, workout_history, profile, fragment_seed):
    """Fragmented renderer for the per-exercise UI (THE BIG WIN).

    ``@st.fragment`` means widget changes inside here (weight typed, reps
    changed, Done clicked, expanders toggled) ONLY invalidate this function's
    output.  Everything outside the fragment — sidebar CSS, weekly plan
    expanders, dashboard metrics, AI Coach chat bubbles, etc. — is FULLY
    SKIPPED on rerender.  Saves ~200-250 ms per keystroke.

    ``fragment_seed`` is never read but acts as a cache invalidation signal:
    the caller bumps it (e.g. to ``time.time_ns()``) when it wants the
    fragment's cached output discarded and rebuilt from scratch.
    """
    # ----- Build previous-performance index O(H) ONCE per fragment render ----
    _previous_performance_index: dict[str, dict[str, float]] = {}
    for _workout in reversed(workout_history or []):
        for _exercise in _workout.get("exercises", []):
            _exercise_key = _exercise.get("name", "").strip().lower()
            if not _exercise_key or _exercise_key in _previous_performance_index:
                continue
            _completed_sets = [
                s
                for s in _exercise.get("sets", [])
                if s.get("completed", False)
            ]
            if _completed_sets:
                _last = _completed_sets[-1]
                _previous_performance_index[_exercise_key] = {
                    "weight_kg": float(_last.get("weight_kg", 0) or 0),
                    "actual_reps": int(_last.get("actual_reps", 0) or 0),
                }

    # ----- Render each exercise -----
    exercises = session.get("exercises", [])
    for exercise_index, exercise in enumerate(exercises, start=0):
        exercise_name = exercise.get("name", f"Exercise {exercise_index + 1}")
        planned_sets = len(exercise.get("sets", []))
        planned_reps = exercise.get("planned_reps", exercise.get("reps", 8))
        completed_sets = sum(
            1 for s in exercise.get("sets", []) if s.get("completed", False)
        )

        with st.expander(
            f"{'✅' if exercise.get('completed') else '⬜'} "
            f"{exercise_name} "
            f"({completed_sets}/{planned_sets} sets)",
            expanded=(exercise_index == 0 and not exercise.get("completed")),
        ):
            with st.container():
                previous = _previous_performance_index.get(
                    exercise_name.strip().lower()
                )
                target_weight, target_reps = get_progression_target(
                    previous, planned_reps
                )

                if previous:
                    st.caption(
                        f"📜 Last session: "
                        f"{previous.get('weight_kg', 0):.1f} kg × "
                        f"{previous.get('actual_reps', 0)} reps"
                    )

                with st.container(border=True):
                    st.markdown(
                        f"**🎯 Progression target: "
                        f"{target_weight:.1f} kg × {target_reps} "
                        f"reps per set**"
                    )

                instructions = get_exercise_instruction(exercise)
                if instructions:
                    st.info(instructions)

                coaching = get_exercise_coaching(exercise)
                with st.expander("💡 Coach cues", expanded=False):
                    st.markdown("**How to perform:**")
                    for idx, step in enumerate(coaching["steps"], start=1):
                        st.write(f"{idx}. {step}")
                    st.markdown(f"**Breathing:** {coaching['breathing']}")
                    st.markdown(f"**Common mistakes:** {coaching['mistakes']}")
                    st.markdown(f"**Easy mode:** {coaching['modification']}")
                    st.markdown(f"**Next level:** {coaching['progression']}")

                equipment = exercise.get("equipment", "Bodyweight")
                if equipment:
                    st.caption(f"🛠️ Equipment required: {equipment}")

                substitutions = get_exercise_substitutions(
                    exercise, profile or {}, limit=3
                )
                if substitutions:
                    substitution_names = [s["name"] for s in substitutions]
                    selected_substitution = st.selectbox(
                        "Safer alternative",
                        ["Keep current exercise"] + substitution_names,
                        key=f"substitution_{exercise_index}",
                    )
                    if (
                        selected_substitution != "Keep current exercise"
                        and st.button(
                            "Use alternative",
                            key=f"use_substitution_{exercise_index}",
                        )
                    ):
                        replacement = next(
                            s
                            for s in substitutions
                            if s["name"] == selected_substitution
                        )
                        replacement["planned_sets"] = exercise.get(
                            "planned_sets",
                            replacement.get("sets", 3),
                        )
                        replacement["planned_reps"] = exercise.get(
                            "planned_reps",
                            replacement.get("reps", 8),
                        )
                        rebuilt = _initialize_session({"exercises": [replacement]})
                        session["exercises"][exercise_index] = rebuilt[
                            "exercises"
                        ][0]
                        st.session_state.active_workout_session = session
                        st.rerun()

                st.divider()

                _render_set_logger(
                    exercise_index, exercise, target_weight, target_reps
                )

            # ----- Post-set: recompute completed for success banner -----
            completed_sets = sum(
                1 for s in exercise.get("sets", []) if s.get("completed", False)
            )
            all_completed = planned_sets > 0 and completed_sets >= planned_sets
            exercise["completed"] = all_completed
            if all_completed:
                st.success("Exercise completed! ✅")

    return session


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
        exercise.get(
            "sets",
            exercise.get(
                "planned_sets",
                3,
            ),
        ),
        3,
    )


def _get_planned_reps(exercise):
    return _parse_reps(
        exercise.get(
            "reps",
            exercise.get(
                "planned_reps",
                8,
            ),
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

    for exercise in session.get(
        "exercises",
        [],
    ):

        exercise_completed = False

        for set_data in exercise.get(
            "sets",
            [],
        ):

            if set_data.get(
                "completed",
                False,
            ):

                total_sets += 1

                weight = _safe_float(
                    set_data.get(
                        "weight_kg",
                        0,
                    )
                )

                reps = _safe_int(
                    set_data.get(
                        "actual_reps",
                        0,
                    )
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


def _save_history(
    history_file,
    history,
    save_json_function,
):
    return save_json_function(
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

    for workout in reversed(
        workout_history or []
    ):

        for exercise in workout.get(
            "exercises",
            [],
        ):

            if (
                exercise.get(
                    "name",
                    "",
                ).strip().lower()
                == exercise_name.strip().lower()
            ):

                sets = exercise.get(
                    "sets",
                    [],
                )

                completed_sets = [
                    item
                    for item in sets
                    if item.get(
                        "completed",
                        False,
                    )
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

    for exercise in workout_plan.get(
        "exercises",
        [],
    ):

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

    if (
        "active_workout_session"
        not in st.session_state
    ):

        st.session_state.active_workout_session = None

    if (
        "workout_session_started"
        not in st.session_state
    ):

        st.session_state.workout_session_started = False

    if (
        "selected_workout_day"
        not in st.session_state
    ):

        st.session_state.selected_workout_day = 0


# ============================================================
# SAVE COMPLETED WORKOUT
# ============================================================

def _save_completed_workout(
    completed_workout,
    history_file,
    save_json_function,
    save_supabase_function,
    profile_id,
    use_supabase,
):
    """
    Save completed workout.

    Supabase is the primary persistent storage when enabled.

    Returns:
        "supabase" when Supabase save succeeds.
    """

    # ========================================================
    # SUPABASE PRIMARY STORAGE
    # ========================================================

    if (
        use_supabase
        and profile_id
        and save_supabase_function
    ):

        try:

            saved_result = save_supabase_function(
                profile_id,
                completed_workout,
            )

            # A successful Supabase save must return
            # the inserted row as a dictionary.
            if isinstance(
                saved_result,
                dict,
            ):
                if bust_user_cache is not None:
                    bust_user_cache()
                return "supabase"

            raise RuntimeError(
                "Supabase workout save returned no inserted row."
            )

        except Exception as error:

            st.error(
                "Workout could not be saved to Supabase."
            )
            st.caption(f"Supabase save error: {error}")
            raise

    raise RuntimeError(
        "Supabase storage is required to save completed workouts."
    )


# ============================================================
# RENDER LOGGER
# ============================================================

def render_workout_logger(
    workout_plan,
    workout_history,
    history_file,
    save_json_function,
    save_supabase_function=None,
    profile_id=None,
    use_supabase=False,
    profile=None,
):

    # ============================================================
    # CLOUD SAFETY VALVE: MANUAL EXERCISE LOGGER OVERRIDE
    # ============================================================
    import streamlit as st
    from utils.storage import load_json
    if not workout_plan:
        st.info("No active plan synced yet. You can still log any exercise manually right now!")
        exercises_list = load_json("data/exercises.json", [])
        if exercises_list:
            ex_names = sorted(list({e.get("name") for e in exercises_list if e.get("name")}))
            chosen_ex = st.selectbox("Choose Exercise to Log:", ex_names)
            if chosen_ex:
                workout_plan = [{"day": "Manual Session", "exercises": [{"name": chosen_ex, "sets": [{"weight_kg": 0.0, "actual_reps": 0, "completed": False} for _ in range(3)]}]}]


    # ============================================================


    _ensure_session_state()

    if not workout_plan:

        st.info(
            "Generate a workout plan first."
        )

        return workout_history

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
        profile = profile or {}

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

        return workout_history

    # ========================================================
    # ACTIVE WORKOUT
    # ========================================================

    session = (
        st.session_state.active_workout_session
    )

    if not session:

        st.session_state.workout_session_started = False

        st.rerun()

        return workout_history

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
        _calculate_workout_totals(
            session
        )
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

    warmup_rows = selected_workout.get("warmup_exercises") or []
    cooldown_rows = selected_workout.get("cooldown_exercises") or []

    with st.expander(
        f"🔥 Warm-up · {len(warmup_rows)} exercises · review before lifting",
        expanded=False,
    ):
        for wex in warmup_rows:
            with st.container(border=True):
                wcols = st.columns([3, 1, 2, 5])
                wcols[0].markdown(f"**{wex.get('name', '')}**")
                wcols[1].write(f"{wex.get('sets', '')} × {wex.get('reps', '')}")
                wcols[2].write(wex.get("equipment", ""))
                wcols[3].write(wex.get("instructions", ""))

    # ========================================================
    # EXERCISES (fragmented — saves ~200-250 ms on every widget change)
    # ========================================================
    #
    # ``fragment_seed`` forces the decorated @st.fragment function to discard
    # its cached output on every FULL page rerun.  When the user clicks
    # something INSIDE the exercises fragment (typing weight, done checkbox,
    # etc), @st.fragment skips re-evaluating the rest of render_workout_logger
    # AND everything above it in app.py — which is the whole point.  But when
    # something OUTSIDE the fragment causes a full rerun (e.g. user clicks
    # "Start Workout" which rebuilds exercises / resets session, or user
    # navigates back to My Workout from a different tab), we pass a new
    # ``time.time_ns()`` seed so the fragment definitely rebuilds against the
    # latest ``session``, ``profile``, and ``workout_history`` rather than
    # serving stale widget DOM.
    _render_exercises_fragment(
        session=session,
        workout_history=workout_history,
        profile=profile,
        fragment_seed=time.time_ns(),
    )

    with st.expander(
        f"🧊 Cool-down · {len(cooldown_rows)} exercises · static stretches",
        expanded=False,
    ):
        for cex in cooldown_rows:
            with st.container(border=True):
                ccols = st.columns([3, 1, 2, 5])
                ccols[0].markdown(f"**{cex.get('name', '')}**")
                ccols[1].write(f"{cex.get('sets', '')} × {cex.get('reps', '')}")
                ccols[2].write(cex.get("equipment", ""))
                ccols[3].write(cex.get("instructions", ""))

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

    # ============================================================
    # PORTFOLIO METRICS LOOP: POST-WORKOUT READINESS CHECK
    # ============================================================
    st.write("---")
    
    with st.form(key="fatigue_readiness_v2_form"):
        st.markdown("### Post-Workout Fatigue and Readiness Check")
        st.caption("Rate metrics to train your closed-loop AI model layer.")
        rpe = st.slider("Session Exertion (RPE 1-10):", min_value=1, max_value=10, value=7, step=1)
        soreness = st.slider("Muscle/Joint Soreness (1-5):", min_value=1, max_value=5, value=2, step=1)
        energy = st.slider("Remaining Energy Reserves (1-5):", min_value=1, max_value=5, value=3, step=1)
        submit = st.form_submit_button(label="Analyze Performance and Load Coach Advice")
    if submit:
        import modules.ai_coach as ai_coach
        ai_coach.render_ai_coach_dashboard_ui({"rpe":rpe,"soreness":soreness,"energy":energy}, st.session_state.get("current_workout_name", "Akhada Session"))
        st.slider("Session Exertion (RPE 1-10):", min_value=1, max_value=10, value=7, step=1, key="feedback_rpe")
    
    
    st.write("")

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
                "rpe": int(st.session_state.get("feedback_rpe", 7)),
                "soreness": int(st.session_state.get("feedback_soreness", 2)),
                "energy": int(st.session_state.get("feedback_energy", 3)),
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
                "total_exercises": len(
                    session.get(
                        "exercises",
                        [],
                    )
                ),
                "intensity": selected_workout.get(
                    "intensity"
                ),
                "notes": session.get(
                    "notes",
                    "",
                ),
                "exercises": session.get(
                    "exercises",
                    [],
                ),
            }

            # ------------------------------------------------
            # SAVE TO SUPABASE / LOCAL
            # ------------------------------------------------

            storage_used = _save_completed_workout(
                completed_workout=completed_workout,
                history_file=history_file,
                save_json_function=save_json_function,
                save_supabase_function=save_supabase_function,
                profile_id=profile_id,
                use_supabase=use_supabase,
            )

            # ------------------------------------------------
            # UPDATE LOCAL SESSION HISTORY
            # ------------------------------------------------

            updated_history = list(
                workout_history or []
            )

            updated_history.append(
                completed_workout
            )

            st.session_state.workout_history = (
                updated_history
            )

            # Clear active session.

            st.session_state.active_workout_session = None

            st.session_state.workout_session_started = False

            # ------------------------------------------------
            # SUCCESS MESSAGE
            # ------------------------------------------------

            st.success(
                "🎉 Workout completed and saved to Supabase!"
            )

            st.balloons()

            # ------------------------------------------------
            # COMPLETION SUMMARY
            # ------------------------------------------------

            st.subheader(
                "📊 Workout Summary"
            )

            col1, col2, col3, col4 = st.columns(4)

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
                "Your workout has been saved to Supabase and will be "
                "available to Workout History, Progress, and AI Coach."
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

    return workout_history
