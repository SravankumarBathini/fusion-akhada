"""Pure dashboard metrics used by the Streamlit presentation."""

from datetime import datetime, timedelta

from domain.performance import get_exercise_performance


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
