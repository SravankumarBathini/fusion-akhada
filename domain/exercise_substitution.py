"""Safe exercise substitutions based on training focus and equipment."""

import functools
from typing import Any

from domain.exercise_rules import normalize_text


SUBSTITUTION_CATALOG = {
    "chest": [
        ("Push-Up", "Bodyweight", "Chest", "Horizontal Push"),
        ("Dumbbell Floor Press", "Dumbbells", "Chest", "Horizontal Push"),
        ("Incline Push-Up", "Bodyweight", "Chest", "Horizontal Push"),
    ],
    "back": [
        ("Dumbbell Row", "Dumbbells", "Back", "Horizontal Pull"),
        ("Inverted Row", "Bodyweight", "Back", "Horizontal Pull"),
        ("Band Row", "Resistance Band", "Back", "Horizontal Pull"),
    ],
    "shoulder": [
        ("Pike Push-Up", "Bodyweight", "Shoulders", "Vertical Push"),
        ("Dumbbell Shoulder Press", "Dumbbells", "Shoulders", "Vertical Push"),
        ("Band Pull-Apart", "Resistance Band", "Shoulders", "Horizontal Pull"),
    ],
    "quad": [
        ("Bodyweight Squat", "Bodyweight", "Quadriceps", "Squat"),
        ("Reverse Lunge", "Bodyweight", "Quadriceps", "Lunge"),
        ("Goblet Squat", "Dumbbells", "Quadriceps", "Squat"),
    ],
    "hamstring": [
        ("Glute Bridge", "Bodyweight", "Hamstrings", "Hip Hinge"),
        ("Dumbbell Romanian Deadlift", "Dumbbells", "Hamstrings", "Hip Hinge"),
        ("Single-Leg Glute Bridge", "Bodyweight", "Hamstrings", "Hip Hinge"),
    ],
    "glute": [
        ("Glute Bridge", "Bodyweight", "Glutes", "Hip Hinge"),
        ("Reverse Lunge", "Bodyweight", "Glutes", "Lunge"),
        ("Dumbbell Hip Thrust", "Dumbbells", "Glutes", "Hip Hinge"),
    ],
    "core": [
        ("Dead Bug", "Bodyweight", "Core", "Anti-Extension"),
        ("Plank", "Bodyweight", "Core", "Anti-Extension"),
        ("Bird Dog", "Bodyweight", "Core", "Anti-Rotation"),
    ],
    "bicep": [
        ("Dumbbell Curl", "Dumbbells", "Biceps", "Elbow Flexion"),
        ("Band Curl", "Resistance Band", "Biceps", "Elbow Flexion"),
        ("Chin-Up", "Bodyweight", "Biceps", "Vertical Pull"),
    ],
    "tricep": [
        ("Close-Grip Push-Up", "Bodyweight", "Triceps", "Horizontal Push"),
        ("Dumbbell Overhead Extension", "Dumbbells", "Triceps", "Elbow Extension"),
        ("Band Pressdown", "Resistance Band", "Triceps", "Elbow Extension"),
    ],
}


def _available_equipment(profile: dict[str, Any]) -> set[str]:
    equipment = profile.get("equipment", [])
    if not isinstance(equipment, list):
        equipment = [equipment]
    available = {normalize_text(item) for item in equipment if item}
    if not available or "no equipment" in available:
        available.add("bodyweight")
    return available


def _matches_equipment(required: str, available: set[str]) -> bool:
    required_text = normalize_text(required)
    if required_text in {"bodyweight", "none", "no equipment"}:
        return True
    return required_text in available


@functools.lru_cache(maxsize=128)
def _cached_substitution_candidates(
    source_name: str,
    focus: str,
    avoided: str,
    available_frozen: tuple[str, ...],
    limit: int,
) -> tuple[tuple[str, str, str, str], ...]:
    """Return substitution (name, equipment, muscle, pattern) tuples cached.

    Takes only hashable primitives (strings + tuple of strings) so the
    result can live in ``lru_cache`` across all workout renders.  The
    public wrapper re-attaches the caller's ``exercise`` fields afterwards
    so we avoid hashing dict inputs.
    """
    available_set = set(available_frozen)
    avoided_set = set(a.strip() for a in avoided.split(",") if a.strip()) if avoided else set()

    key = next(
        (catalog_key for catalog_key in SUBSTITUTION_CATALOG if catalog_key in focus),
        None,
    )
    if key is None:
        return tuple()

    substitutions: list[tuple[str, str, str, str]] = []
    for name, equipment, muscle, pattern in SUBSTITUTION_CATALOG[key]:
        candidate_name = normalize_text(name)
        if candidate_name == source_name:
            continue
        if avoided_set and any(normalize_text(a) == candidate_name for a in avoided_set):
            continue
        if not _matches_equipment(equipment, available_set):
            continue
        substitutions.append((name, equipment, muscle, pattern))
        if len(substitutions) >= max(1, limit):
            break
    return tuple(substitutions)


def get_exercise_substitutions(
    exercise: dict[str, Any],
    profile: dict[str, Any],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return distinct alternatives that match the exercise's muscle focus."""
    source_name = normalize_text(exercise.get("name", ""))
    focus = normalize_text(
        exercise.get("primary_muscle")
        or exercise.get("movement_pattern")
        or "full body"
    )
    avoided_raw = profile.get("exercises_to_avoid") or ""
    avoided = normalize_text(
        ",".join(avoided_raw) if isinstance(avoided_raw, list) else str(avoided_raw)
    )
    available_frozen = tuple(sorted(_available_equipment(profile)))

    cached = _cached_substitution_candidates(
        source_name,
        focus,
        avoided,
        available_frozen,
        int(limit),
    )

    substitutions: list[dict[str, Any]] = []
    for name, equipment, muscle, pattern in cached:
        replacement = dict(exercise)
        replacement.update(
            {
                "name": name,
                "equipment": equipment,
                "primary_muscle": muscle,
                "movement_pattern": pattern,
            }
        )
        substitutions.append(replacement)
    return substitutions
