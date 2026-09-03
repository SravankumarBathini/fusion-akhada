"""Workout-plan application use cases.

The local generator is deterministic and pure; integrations such as Gemini
remain behind the existing ``modules.workout_generator`` compatibility API.
"""

from typing import Any

from domain.workout_generation import generate_weekly_plan as generate_local_weekly_plan
from domain.workout_validation import has_duplicate_exercises, normalize_workout_plan


def generate_workout_plan(
    profile: dict[str, Any],
    exercise_database: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate a local plan using the domain rules."""

    return generate_local_weekly_plan(profile, exercise_database)


__all__ = [
    "generate_workout_plan",
    "generate_local_weekly_plan",
    "has_duplicate_exercises",
    "normalize_workout_plan",
]
