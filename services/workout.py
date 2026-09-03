"""Backward-compatible import facade for workout domain rules."""
from domain.workout_generation import *  # noqa: F401,F403
from domain.workout_validation import normalize_workout_plan
