"""Pure exercise performance aggregation."""

from datetime import datetime

from domain.exercise_rules import parse_history_datetime


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
