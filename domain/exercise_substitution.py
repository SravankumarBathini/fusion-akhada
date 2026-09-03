"""Safe exercise substitutions based on training focus and equipment."""

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
    avoided = normalize_text(profile.get("exercises_to_avoid", ""))
    available = _available_equipment(profile)

    key = next((key for key in SUBSTITUTION_CATALOG if key in focus), None)
    if key is None:
        return []

    substitutions = []
    for name, equipment, muscle, pattern in SUBSTITUTION_CATALOG[key]:
        if normalize_text(name) == source_name:
            continue
        if avoided and normalize_text(name) in avoided:
            continue
        if not _matches_equipment(equipment, available):
            continue
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
        if len(substitutions) >= max(1, limit):
            break
    return substitutions
