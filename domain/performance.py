"""Pure exercise performance aggregation."""

from datetime import datetime

from domain.exercise_rules import parse_history_datetime


def get_progression_target(
    previous: dict | None,
    planned_reps: int,
    max_reps: int = 15,
) -> tuple[float, int]:
    """Calculate the next safe weight and rep target from prior performance."""
    try:
        target_reps = max(1, int(planned_reps))
    except (TypeError, ValueError):
        target_reps = 8

    if not isinstance(previous, dict):
        return 0.0, target_reps

    try:
        previous_weight = max(0.0, float(previous.get("weight_kg", 0.0)))
    except (TypeError, ValueError):
        previous_weight = 0.0

    try:
        previous_reps = max(0, int(previous.get("actual_reps", 0)))
    except (TypeError, ValueError):
        previous_reps = 0

    if previous_weight <= 0:
        return 0.0, target_reps

    if previous_reps >= target_reps:
        return previous_weight, min(previous_reps + 1, max_reps)

    return previous_weight, max(previous_reps, target_reps)


def get_exercise_performance(history):
    performance = {}

    chronological_history = []

    for workout in history:

        workout_datetime = (
            parse_history_datetime(
                workout
            )
        )

        chronological_history.append(
            (
                workout_datetime
                or datetime.min,
                workout,
            )
        )

    chronological_history.sort(
        key=lambda item: item[0]
    )

    for _, workout in chronological_history:

        workout_date = workout.get(
            "date",
            "",
        )

        exercises = workout.get(
            "exercises",
            [],
        )

        for exercise in exercises:

            if not exercise.get(
                "completed",
                False,
            ):
                continue

            name = exercise.get(
                "name",
                "Exercise",
            )

            if name not in performance:
                performance[name] = []

            weight = exercise.get(
                "weight_kg",
                0,
            )

            reps = exercise.get(
                "actual_reps",
                0,
            )

            try:
                weight = float(weight)
            except (
                TypeError,
                ValueError,
            ):
                weight = 0.0

            try:
                reps = int(reps)
            except (
                TypeError,
                ValueError,
            ):
                reps = 0

            volume = weight * reps

            performance[name].append(
                {
                    "date": workout_date,
                    "weight_kg": weight,
                    "actual_reps": reps,
                    "planned_sets": exercise.get(
                        "planned_sets",
                        0,
                    ),
                    "planned_reps": exercise.get(
                        "planned_reps",
                        "",
                    ),
                    "volume": volume,
                }
            )

    return performance
