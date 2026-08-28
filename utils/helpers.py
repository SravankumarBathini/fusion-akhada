from datetime import datetime, timedelta


def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            normalize_text(item)
            for item in value
        )

    return str(value).strip().lower()


def exercise_is_avoided(exercise, avoided_exercises):
    exercise_name = normalize_text(
        exercise.get("name", "")
    )

    avoided_text = normalize_text(
        avoided_exercises
    )

    if not avoided_text:
        return False

    return exercise_name in avoided_text


def exercise_is_preferred(exercise, preferred_exercises):
    exercise_name = normalize_text(
        exercise.get("name", "")
    )

    preferred_text = normalize_text(
        preferred_exercises
    )

    if not preferred_text:
        return False

    return exercise_name in preferred_text


def parse_history_datetime(workout):
    date_text = str(
        workout.get(
            "date",
            "",
        )
    ).strip()

    time_text = str(
        workout.get(
            "time",
            "",
        )
    ).strip()

    if not date_text:
        return None

    combined = date_text

    if time_text:
        combined = f"{date_text} {time_text}"

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                combined,
                fmt,
            )
        except ValueError:
            continue

    return None


def get_completed_exercises_count(history):
    total = 0

    for workout in history:
        exercises = workout.get(
            "exercises",
            [],
        )

        for exercise in exercises:
            if exercise.get(
                "completed",
                False,
            ):
                total += 1

    return total


def get_workouts_this_week(history):
    today = datetime.now().date()

    start_of_week = (
        today
        - timedelta(days=today.weekday())
    )

    count = 0

    for workout in history:
        workout_datetime = parse_history_datetime(
            workout
        )

        if workout_datetime is None:
            continue

        if (
            start_of_week
            <= workout_datetime.date()
            <= today
        ):
            count += 1

    return count


def get_workouts_this_month(history):
    today = datetime.now().date()

    count = 0

    for workout in history:
        workout_datetime = parse_history_datetime(
            workout
        )

        if workout_datetime is None:
            continue

        if (
            workout_datetime.year == today.year
            and workout_datetime.month == today.month
        ):
            count += 1

    return count