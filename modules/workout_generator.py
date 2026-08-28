# ============================================================
# WORKOUT GENERATOR
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            normalize_text(item)
            for item in value
        )

    return str(value).strip().lower()


def normalize_workout_plan(plan):
    normalized_plan = []

    if not isinstance(plan, list):
        return normalized_plan

    for day in plan:
        if not isinstance(day, dict):
            continue

        normalized_day = dict(day)

        normalized_day.setdefault(
            "day",
            len(normalized_plan) + 1,
        )
        normalized_day.setdefault(
            "name",
            "Workout",
        )
        normalized_day.setdefault(
            "duration",
            45,
        )
        normalized_day.setdefault(
            "intensity",
            "Moderate",
        )
        normalized_day.setdefault(
            "warmup",
            "5-10 minutes",
        )
        normalized_day.setdefault(
            "cooldown",
            "5 minutes",
        )
        normalized_day.setdefault(
            "exercises",
            [],
        )

        normalized_exercises = []

        for exercise in normalized_day.get(
            "exercises",
            [],
        ):
            if not isinstance(exercise, dict):
                continue

            normalized_exercise = dict(exercise)

            normalized_exercise.setdefault(
                "name",
                "Exercise",
            )
            normalized_exercise.setdefault(
                "equipment",
                "None",
            )
            normalized_exercise.setdefault(
                "sets",
                3,
            )
            normalized_exercise.setdefault(
                "reps",
                "8-12",
            )
            normalized_exercise.setdefault(
                "rest",
                "60-90 sec",
            )

            normalized_exercise.setdefault(
                "type",
                normalized_exercise.get(
                    "exercise_type",
                    "Strength",
                ),
            )

            normalized_exercise.setdefault(
                "exercise_type",
                normalized_exercise.get(
                    "type",
                    "Strength",
                ),
            )

            normalized_exercise.setdefault(
                "primary_muscle",
                "Full Body",
            )

            normalized_exercise.setdefault(
                "secondary_muscles",
                [],
            )

            normalized_exercise.setdefault(
                "movement_pattern",
                "",
            )

            normalized_exercise.setdefault(
                "difficulty",
                "Beginner",
            )

            normalized_exercise.setdefault(
                "instructions",
                "",
            )

            normalized_exercises.append(
                normalized_exercise
            )

        normalized_day["exercises"] = (
            normalized_exercises
        )

        normalized_plan.append(
            normalized_day
        )

    return normalized_plan


# ============================================================
# TRAINING SPLITS
# ============================================================

def get_training_split(days_per_week):
    splits = {
        1: [
            "Full Body"
        ],

        2: [
            "Full Body",
            "Full Body",
        ],

        3: [
            "Full Body",
            "Upper Body",
            "Lower Body",
        ],

        4: [
            "Upper Body",
            "Lower Body",
            "Upper Body",
            "Lower Body",
        ],

        5: [
            "Chest & Triceps",
            "Back & Biceps",
            "Legs",
            "Shoulders & Core",
            "Full Body",
        ],

        6: [
            "Chest & Triceps",
            "Back & Biceps",
            "Legs",
            "Shoulders",
            "Arms & Core",
            "Full Body",
        ],

        7: [
            "Upper Body",
            "Lower Body",
            "Upper Body",
            "Lower Body",
            "Upper Body",
            "Lower Body",
            "Full Body",
        ],
    }

    return splits.get(
        days_per_week,
        splits[3],
    )


# ============================================================
# MUSCLE AREA MAPPING
# ============================================================

MUSCLE_AREAS = {
    "Full Body": [
        "Full Body",
        "Chest",
        "Back",
        "Shoulders",
        "Biceps",
        "Triceps",
        "Quadriceps",
        "Hamstrings",
        "Glutes",
        "Legs",
        "Core",
    ],

    "Upper Body": [
        "Chest",
        "Back",
        "Shoulders",
        "Biceps",
        "Triceps",
    ],

    "Lower Body": [
        "Quadriceps",
        "Hamstrings",
        "Glutes",
        "Legs",
    ],

    "Chest & Triceps": [
        "Chest",
        "Triceps",
    ],

    "Back & Biceps": [
        "Back",
        "Biceps",
    ],

    "Legs": [
        "Quadriceps",
        "Hamstrings",
        "Glutes",
        "Legs",
    ],

    "Shoulders & Core": [
        "Shoulders",
        "Core",
    ],

    "Shoulders": [
        "Shoulders",
    ],

    "Arms & Core": [
        "Biceps",
        "Triceps",
        "Core",
    ],
}


# ============================================================
# TRAINING PARAMETERS
# ============================================================

def get_training_parameters(
    goal,
    style,
    level,
):
    goal_text = str(goal).lower()
    style_text = str(style).lower()
    level_text = str(level).lower()

    if (
        "strength" in goal_text
        or "strength" in style_text
    ):
        if level_text == "beginner":
            return 3, "6-10", "90-120 sec"

        if level_text == "intermediate":
            return 4, "5-8", "120 sec"

        return 4, "3-6", "150-180 sec"

    if (
        "muscle" in goal_text
        or "hypertrophy" in style_text
    ):
        if level_text == "beginner":
            return 2, "8-12", "60-90 sec"

        if level_text == "intermediate":
            return 3, "8-12", "60-90 sec"

        return 4, "6-12", "90 sec"

    if (
        "fat" in goal_text
        or "conditioning" in style_text
    ):
        return 3, "10-15", "30-60 sec"

    if (
        "endurance" in goal_text
        or "cardio" in style_text
    ):
        return 2, "12-20", "30-60 sec"

    return 3, "8-12", "60-90 sec"


# ============================================================
# EXERCISE COUNT
# ============================================================

def get_exercise_count(duration):
    duration = int(duration)

    if duration <= 20:
        return 3

    if duration <= 40:
        return 4

    if duration <= 60:
        return 5

    return 6


# ============================================================
# EXERCISE PREFERENCES
# ============================================================

def exercise_is_avoided(
    exercise,
    avoided_exercises,
):
    exercise_name = normalize_text(
        exercise.get("name", "")
    )

    avoided_text = normalize_text(
        avoided_exercises
    )

    if not avoided_text:
        return False

    return exercise_name in avoided_text


def exercise_is_preferred(
    exercise,
    preferred_exercises,
):
    exercise_name = normalize_text(
        exercise.get("name", "")
    )

    preferred_text = normalize_text(
        preferred_exercises
    )

    if not preferred_text:
        return False

    return exercise_name in preferred_text


# ============================================================
# EXERCISE FILTERING
# ============================================================

def filter_exercises(
    profile,
    target_areas,
    exercise_database,
):
    equipment = profile.get(
        "equipment",
        [],
    )

    avoided_exercises = profile.get(
        "exercises_to_avoid",
        "",
    )

    if not isinstance(equipment, list):
        equipment = [equipment]

    available_equipment = {
        normalize_text(item)
        for item in equipment
        if normalize_text(item)
    }

    filtered = []

    for exercise in exercise_database:

        if not isinstance(exercise, dict):
            continue

        if exercise_is_avoided(
            exercise,
            avoided_exercises,
        ):
            continue

        exercise_equipment = normalize_text(
            exercise.get("equipment", "")
        )

        if (
            available_equipment
            and "no equipment"
            not in available_equipment
            and exercise_equipment
            and exercise_equipment
            not in available_equipment
        ):
            continue

        primary_muscle = normalize_text(
            exercise.get(
                "primary_muscle",
                "",
            )
        )

        secondary_muscles = normalize_text(
            exercise.get(
                "secondary_muscles",
                "",
            )
        )

        target_match = False

        for area in target_areas:

            area_text = normalize_text(area)

            if area_text in primary_muscle:
                target_match = True
                break

            if area_text in secondary_muscles:
                target_match = True
                break

        if target_match:
            filtered.append(exercise)

    return filtered


# ============================================================
# EXERCISE SCORING
# ============================================================

def score_exercise(
    exercise,
    profile,
    target_areas,
    used_exercises,
    used_patterns,
):
    score = 0

    primary_muscle = normalize_text(
        exercise.get(
            "primary_muscle",
            "",
        )
    )

    movement_pattern = normalize_text(
        exercise.get(
            "movement_pattern",
            "",
        )
    )

    exercise_name = normalize_text(
        exercise.get(
            "name",
            "",
        )
    )

    preferred_exercises = profile.get(
        "exercises_enjoy",
        profile.get(
            "preferred_exercises",
            "",
        ),
    )

    for area in target_areas:

        area_text = normalize_text(area)

        if area_text in primary_muscle:
            score += 10

    if exercise_is_preferred(
        exercise,
        preferred_exercises,
    ):
        score += 15

    exercise_type = normalize_text(
        exercise.get(
            "exercise_type",
            "",
        )
    )

    if "compound" in exercise_type:
        score += 5

    if (
        movement_pattern
        and movement_pattern
        not in used_patterns
    ):
        score += 5

    if exercise_name in used_exercises:
        score -= 20

    return score


# ============================================================
# EXERCISE SELECTION
# ============================================================

def select_exercises(
    profile,
    target_areas,
    exercise_count,
    used_exercises,
    used_patterns,
    exercise_database,
):
    candidates = filter_exercises(
        profile,
        target_areas,
        exercise_database,
    )

    scored = []

    for exercise in candidates:

        score = score_exercise(
            exercise,
            profile,
            target_areas,
            used_exercises,
            used_patterns,
        )

        scored.append(
            (
                score,
                exercise,
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    selected = []

    for _, exercise in scored:

        exercise_name = normalize_text(
            exercise.get(
                "name",
                "",
            )
        )

        movement_pattern = normalize_text(
            exercise.get(
                "movement_pattern",
                "",
            )
        )

        if exercise_name in used_exercises:
            continue

        if (
            movement_pattern
            and movement_pattern
            in used_patterns
        ):
            continue

        selected.append(exercise)

        if exercise_name:
            used_exercises.add(
                exercise_name
            )

        if movement_pattern:
            used_patterns.add(
                movement_pattern
            )

        if len(selected) >= exercise_count:
            break

    # Fallback if there aren't enough unique exercises.
    if len(selected) < exercise_count:

        for _, exercise in scored:

            if exercise in selected:
                continue

            selected.append(exercise)

            if len(selected) >= exercise_count:
                break

    return selected


# ============================================================
# GENERATE WORKOUT DAY
# ============================================================

def generate_workout_day(
    profile,
    day_number,
    day_name,
    used_exercises,
    used_patterns,
    exercise_database,
):
    duration = int(
        profile.get(
            "workout_duration",
            45,
        )
    )

    intensity = profile.get(
        "workout_intensity",
        "Moderate",
    )

    goal = profile.get(
        "fitness_goal",
        "Build muscle",
    )

    style = profile.get(
        "workout_style",
        "Mixed Training",
    )

    level = profile.get(
        "fitness_level",
        "Beginner",
    )

    sets, reps, rest = (
        get_training_parameters(
            goal,
            style,
            level,
        )
    )

    exercise_count = get_exercise_count(
        duration
    )

    target_areas = profile.get(
        "target_areas",
        [],
    )

    if not target_areas:
        target_areas = MUSCLE_AREAS.get(
            day_name,
            ["Full Body"],
        )
    else:
        split_areas = MUSCLE_AREAS.get(
            day_name,
            [],
        )

        matching_areas = [
            area
            for area in target_areas
            if area in split_areas
        ]

        if matching_areas:
            target_areas = matching_areas
        else:
            target_areas = split_areas or [
                "Full Body"
            ]

    selected_exercises = select_exercises(
        profile,
        target_areas,
        exercise_count,
        used_exercises,
        used_patterns,
        exercise_database,
    )

    exercises = []

    for exercise in selected_exercises:

        exercise_data = {
            "name": exercise.get(
                "name",
                "Exercise",
            ),
            "equipment": exercise.get(
                "equipment",
                "No equipment",
            ),
            "sets": sets,
            "reps": reps,
            "rest": rest,
            "type": exercise.get(
                "exercise_type",
                "Strength",
            ),
            "exercise_type": exercise.get(
                "exercise_type",
                "Strength",
            ),
            "primary_muscle": exercise.get(
                "primary_muscle",
                "",
            ),
            "secondary_muscles": exercise.get(
                "secondary_muscles",
                [],
            ),
            "movement_pattern": exercise.get(
                "movement_pattern",
                "",
            ),
            "difficulty": exercise.get(
                "difficulty",
                level,
            ),
            "instructions": exercise.get(
                "instructions",
                "",
            ),
        }

        exercises.append(
            exercise_data
        )

    return {
        "day": day_number,
        "name": day_name,
        "duration": duration,
        "intensity": intensity,
        "warmup": "5-10 minutes",
        "cooldown": "5 minutes",
        "exercises": exercises,
    }


# ============================================================
# GENERATE WEEKLY PLAN
# ============================================================

def generate_weekly_plan(
    profile,
    exercise_database,
):
    days_per_week = int(
        profile.get(
            "days_per_week",
            3,
        )
    )

    split = get_training_split(
        days_per_week
    )

    used_exercises = set()
    used_patterns = set()

    weekly_plan = []

    for day_number, day_name in enumerate(
        split,
        start=1,
    ):

        workout_day = generate_workout_day(
            profile,
            day_number,
            day_name,
            used_exercises,
            used_patterns,
            exercise_database,
        )

        weekly_plan.append(
            workout_day
        )

    return weekly_plan