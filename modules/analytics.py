from datetime import datetime

from domain.exercise_rules import (
    get_completed_exercises_count,
    get_workouts_this_month,
    get_workouts_this_week,
    parse_history_datetime,
)


from domain.performance import get_exercise_performance


# ============================================================
# EXERCISE PERFORMANCE
# ============================================================

# ============================================================
# EXERCISE SUMMARY
# ============================================================

def calculate_exercise_summary(performance):
    summaries = []

    for name, entries in performance.items():

        if not entries:
            continue

        best_weight = max(
            entry.get(
                "weight_kg",
                0,
            )
            for entry in entries
        )

        best_reps = max(
            entry.get(
                "actual_reps",
                0,
            )
            for entry in entries
        )

        total_volume = sum(
            entry.get(
                "volume",
                0,
            )
            for entry in entries
        )

        latest_entry = entries[-1]

        summaries.append(
            {
                "Exercise": name,
                "Sessions": len(entries),
                "Latest Weight (kg)": latest_entry.get(
                    "weight_kg",
                    0,
                ),
                "Best Weight (kg)": best_weight,
                "Latest Reps": latest_entry.get(
                    "actual_reps",
                    0,
                ),
                "Best Reps": best_reps,
                "Total Volume (kg)": total_volume,
            }
        )

    summaries.sort(
        key=lambda item: item["Sessions"],
        reverse=True,
    )

    return summaries


# ============================================================
# PERSONAL RECORDS
# ============================================================

def calculate_personal_records(performance):
    records = []

    for name, entries in performance.items():

        if not entries:
            continue

        best_weight_entry = max(
            entries,
            key=lambda entry: (
                entry.get(
                    "weight_kg",
                    0,
                ),
                entry.get(
                    "actual_reps",
                    0,
                ),
            ),
        )

        best_weight = float(
            best_weight_entry.get(
                "weight_kg",
                0,
            )
        )

        best_reps_entry = max(
            entries,
            key=lambda entry: (
                entry.get(
                    "actual_reps",
                    0,
                ),
                entry.get(
                    "weight_kg",
                    0,
                ),
            ),
        )

        best_reps = int(
            best_reps_entry.get(
                "actual_reps",
                0,
            )
        )

        best_volume_entry = max(
            entries,
            key=lambda entry: entry.get(
                "volume",
                0,
            ),
        )

        best_volume = float(
            best_volume_entry.get(
                "volume",
                0,
            )
        )

        records.append(
            {
                "Exercise": name,
                "Best Weight (kg)": best_weight,
                "Weight PR Date": best_weight_entry.get(
                    "date",
                    "-",
                ),
                "Best Reps": best_reps,
                "Reps PR Date": best_reps_entry.get(
                    "date",
                    "-",
                ),
                "Best Volume (kg)": best_volume,
                "Volume PR Date": best_volume_entry.get(
                    "date",
                    "-",
                ),
                "Sessions": len(entries),
            }
        )

    records.sort(
        key=lambda item: item[
            "Best Weight (kg)"
        ],
        reverse=True,
    )

    return records


# ============================================================
# PROGRESS CHANGE
# ============================================================

def get_progress_change(entries):
    if len(entries) < 2:
        return None

    first = entries[0]
    latest = entries[-1]

    first_weight = float(
        first.get(
            "weight_kg",
            0,
        )
    )

    latest_weight = float(
        latest.get(
            "weight_kg",
            0,
        )
    )

    if first_weight > 0:

        weight_change = (
            latest_weight
            - first_weight
        )

        percentage = (
            weight_change
            / first_weight
            * 100
        )

        return {
            "weight_change": weight_change,
            "percentage": percentage,
        }

    return {
        "weight_change": (
            latest_weight
            - first_weight
        ),
        "percentage": None,
    }


# ============================================================
# TRAINING INTELLIGENCE
# ============================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def _sorted_history(history):
    return sorted(
        history,
        key=lambda workout: (
            parse_history_datetime(workout)
            or datetime.min
        ),
    )


def calculate_total_volume(history):
    total_volume = 0.0

    for workout in history:

        workout_volume = _safe_float(
            workout.get(
                "total_volume",
                0,
            )
        )

        if workout_volume > 0:
            total_volume += workout_volume
            continue

        for exercise in workout.get(
            "exercises",
            [],
        ):

            for set_data in exercise.get(
                "sets",
                [],
            ):

                if not set_data.get(
                    "completed",
                    False,
                ):
                    continue

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

                total_volume += (
                    weight * reps
                )

    return total_volume


def calculate_training_streak(history):
    """
    Calculate consecutive training days ending at
    the most recent logged workout date.
    """

    if not history:
        return 0

    dates = set()

    for workout in history:

        workout_datetime = (
            parse_history_datetime(
                workout
            )
        )

        if workout_datetime:
            dates.add(
                workout_datetime.date()
            )

    if not dates:
        return 0

    sorted_dates = sorted(
        dates,
        reverse=True,
    )

    streak = 1
    current_date = sorted_dates[0]

    for next_date in sorted_dates[1:]:

        if (
            current_date
            - next_date
        ).days == 1:

            streak += 1
            current_date = next_date

        else:
            break

    return streak


def calculate_exercise_frequency(history):
    frequency = {}

    for workout in history:

        for exercise in workout.get(
            "exercises",
            [],
        ):

            if not exercise.get(
                "completed",
                False,
            ):
                continue

            name = exercise.get(
                "name",
                "Exercise",
            )

            frequency[name] = (
                frequency.get(name, 0)
                + 1
            )

    return dict(
        sorted(
            frequency.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def calculate_volume_change(history):
    """
    Compare total logged volume from the most recent
    half of workouts against the previous half.

    Requires at least 4 workouts for a meaningful comparison.
    """

    if len(history) < 4:
        return None

    chronological = _sorted_history(
        history
    )

    midpoint = len(chronological) // 2

    previous = chronological[:midpoint]
    recent = chronological[midpoint:]

    previous_volume = calculate_total_volume(
        previous
    )

    recent_volume = calculate_total_volume(
        recent
    )

    if previous_volume == 0:
        percentage = None
    else:
        percentage = (
            (
                recent_volume
                - previous_volume
            )
            / previous_volume
            * 100
        )

    return {
        "previous_volume": previous_volume,
        "recent_volume": recent_volume,
        "percentage": percentage,
    }


def calculate_recent_training_summary(
    history,
):
    """
    Return a compact, AI-friendly summary of the
    user's training data.
    """

    if not history:
        return {
            "workouts_logged": 0,
            "completed_exercises": 0,
            "total_volume": 0.0,
            "training_streak": 0,
            "exercise_frequency": {},
            "volume_change": None,
            "recent_workouts": [],
        }

    performance = get_exercise_performance(
        history
    )

    summaries = calculate_exercise_summary(
        performance
    )

    volume_change = calculate_volume_change(
        history
    )

    chronological = _sorted_history(
        history
    )

    recent_workouts = []

    for workout in chronological[-5:]:

        recent_workouts.append(
            {
                "date": workout.get(
                    "date",
                    "",
                ),
                "workout": workout.get(
                    "workout_name",
                    "Workout",
                ),
                "duration": workout.get(
                    "actual_duration",
                    0,
                ),
                "sets": workout.get(
                    "total_sets",
                    0,
                ),
                "volume": _safe_float(
                    workout.get(
                        "total_volume",
                        0,
                    )
                ),
            }
        )

    return {
        "workouts_logged": len(history),
        "completed_exercises": (
            get_completed_exercises_count(
                history
            )
        ),
        "total_volume": calculate_total_volume(
            history
        ),
        "training_streak": calculate_training_streak(
            history
        ),
        "exercise_frequency": (
            calculate_exercise_frequency(
                history
            )
        ),
        "volume_change": volume_change,
        "exercise_summaries": summaries,
        "recent_workouts": recent_workouts,
    }


def format_training_intelligence(
    history,
):
    """
    Convert training intelligence into a concise
    human-readable block suitable for an AI prompt.
    """

    summary = calculate_recent_training_summary(
        history
    )

    if summary["workouts_logged"] == 0:
        return (
            "No training intelligence is available yet. "
            "The user needs to log workouts first."
        )

    lines = [
        "TRAINING INTELLIGENCE",
        f"Workouts logged: "
        f"{summary['workouts_logged']}",
        f"Completed exercises: "
        f"{summary['completed_exercises']}",
        f"Total logged volume: "
        f"{summary['total_volume']:,.1f} kg",
        f"Training streak: "
        f"{summary['training_streak']} day(s)",
    ]

    frequency = summary[
        "exercise_frequency"
    ]

    if frequency:

        lines.append(
            "Exercise frequency:"
        )

        for name, count in list(
            frequency.items()
        )[:10]:

            lines.append(
                f"- {name}: "
                f"{count} session(s)"
            )

    volume_change = summary[
        "volume_change"
    ]

    if volume_change:

        if volume_change[
            "percentage"
        ] is not None:

            lines.append(
                "Recent vs previous volume: "
                f"{volume_change['percentage']:+.1f}%"
            )

        lines.append(
            f"Previous volume: "
            f"{volume_change['previous_volume']:,.1f} kg"
        )

        lines.append(
            f"Recent volume: "
            f"{volume_change['recent_volume']:,.1f} kg"
        )

    if summary[
        "exercise_summaries"
    ]:

        lines.append(
            "Exercise progression:"
        )

        for item in summary[
            "exercise_summaries"
        ][:10]:

            lines.append(
                f"- {item['Exercise']}: "
                f"{item['Sessions']} sessions, "
                f"latest "
                f"{item['Latest Weight (kg)']} kg × "
                f"{item['Latest Reps']} reps, "
                f"best "
                f"{item['Best Weight (kg)']} kg"
            )

    if summary[
        "recent_workouts"
    ]:

        lines.append(
            "Recent workouts:"
        )

        for workout in summary[
            "recent_workouts"
        ]:

            lines.append(
                f"- {workout['date']} — "
                f"{workout['workout']}: "
                f"{workout['sets']} sets, "
                f"{workout['volume']:,.1f} kg volume"
            )

    return "\n".join(lines)