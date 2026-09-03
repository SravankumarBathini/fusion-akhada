"""Backward-compatible import facade for shared exercise/history helpers."""
from domain.exercise_rules import (
    exercise_is_avoided,
    exercise_is_preferred,
    get_completed_exercises_count,
    get_workouts_this_month,
    get_workouts_this_week,
    normalize_text,
    parse_history_datetime,
)

__all__ = [
    "normalize_text",
    "exercise_is_avoided",
    "exercise_is_preferred",
    "parse_history_datetime",
    "get_completed_exercises_count",
    "get_workouts_this_week",
    "get_workouts_this_month",
]
