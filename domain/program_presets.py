"""Curated training styles combining Indian and Western methods."""

PROGRAM_PRESETS = {
    "Custom": {
        "description": "Build a routine from your own training preferences.",
        "workout_style": None,
    },
    "Akhada Strength": {
        "description": "Progressive strength with dands, bethaks, carries, and compound lifts.",
        "workout_style": "Strength Training",
    },
    "Vyayam Conditioning": {
        "description": "Indian movement flows blended with Western conditioning intervals.",
        "workout_style": "Fat Loss / Conditioning",
    },
    "Hybrid Muscle Builder": {
        "description": "Western hypertrophy structure with traditional Indian finishers.",
        "workout_style": "Hypertrophy / Muscle Building",
    },
}


def get_program_preset(name: str) -> dict[str, str | None]:
    """Return a safe preset definition, falling back to custom."""
    return PROGRAM_PRESETS.get(name, PROGRAM_PRESETS["Custom"])
