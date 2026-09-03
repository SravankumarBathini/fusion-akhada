"""Pure validation and compatibility normalisation for workout plans."""

from collections.abc import Iterable
from typing import Any


def normalize_workout_plan(plan: Any) -> list[Any]:
    """Return a structurally safe copy of a persisted or generated plan."""

    if not isinstance(plan, list):
        return []

    normalized_plan: list[dict[str, Any]] = []
    for day in plan:
        if not isinstance(day, dict):
            continue
        normalized_day = dict(day)
        normalized_day.setdefault("day", len(normalized_plan) + 1)
        normalized_day.setdefault("name", "Workout")
        normalized_day.setdefault("duration", 45)
        normalized_day.setdefault("intensity", "Moderate")
        normalized_day.setdefault("warmup", "5-10 minutes")
        normalized_day.setdefault("cooldown", "5 minutes")

        exercises = normalized_day.get("exercises", [])
        normalized_exercises: list[dict[str, Any]] = []
        if isinstance(exercises, list):
            for exercise in exercises:
                if not isinstance(exercise, dict):
                    continue
                normalized_exercise = dict(exercise)
                normalized_exercise.setdefault("name", "Exercise")
                normalized_exercise.setdefault("equipment", "None")
                normalized_exercise.setdefault("sets", 3)
                normalized_exercise.setdefault("reps", "8-12")
                normalized_exercise.setdefault("rest", "60-90 sec")
                normalized_exercise.setdefault(
                    "type", normalized_exercise.get("exercise_type", "Strength")
                )
                normalized_exercise.setdefault(
                    "exercise_type", normalized_exercise.get("type", "Strength")
                )
                normalized_exercise.setdefault("primary_muscle", "Full Body")
                normalized_exercise.setdefault("secondary_muscles", [])
                normalized_exercise.setdefault("movement_pattern", "")
                normalized_exercise.setdefault("difficulty", "Beginner")
                normalized_exercise.setdefault("instructions", "")
                normalized_exercises.append(normalized_exercise)
        normalized_day["exercises"] = normalized_exercises
        normalized_plan.append(normalized_day)
    return normalized_plan


def has_duplicate_exercises(plan: Any) -> bool:
    """Return whether exercise names repeat (case-insensitively) across a plan."""

    seen: set[str] = set()
    if not isinstance(plan, Iterable) or isinstance(plan, (str, bytes, dict)):
        return False

    for day in plan:
        if not isinstance(day, dict):
            continue
        exercises = day.get("exercises", [])
        if not isinstance(exercises, Iterable) or isinstance(exercises, (str, bytes, dict)):
            continue
        for exercise in exercises:
            if not isinstance(exercise, dict):
                continue
            name = str(exercise.get("name", "")).strip().casefold()
            if name and name in seen:
                return True
            if name:
                seen.add(name)
    return False
