from domain.exercise_rules import (
    normalize_text,
    exercise_is_avoided,
    exercise_is_preferred,
)


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


def get_training_split(days_per_week):
    splits = {
        1: ["Full Body"],
        2: ["Full Body", "Full Body"],
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


def get_training_parameters(goal, style, level):
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


def get_exercise_count(duration, profile=None):
    """Determine exercises per day for the current session.

    The previous algorithm used ``duration`` alone and topped out at 6
    exercises for > 60-minute sessions.  That under-counted for 90-min
    Intermediate Hypertrophy days (where 7-8 is realistic at ~8 min per
    lift including rest + setup).

    The new rules combine *three* profile drivers in addition to
    duration:

    1. ``workout_duration_minutes`` (profile field, e.g. ``90``) — the
       base lift-budget estimate.  1 exercise = ~8-12 minutes for
       hypertrophy / strength, ~6-9 for conditioning.
    2. ``fitness_level`` — Beginner days have a *lower ceiling* because
       form coaching + extended rest take more wall-clock time.
    3. ``days_per_week`` — Higher-frequency splits (6-7d) have a SMALLER
       per-day count because the same muscle groups are hit twice weekly;
       low-frequency (3d full body) need LARGER per-day counts to cover
       every major group in one hit.

    Finally, we apply a FLOOR guarantee — the user explicitly said
    ``min 5 all the time``.  Beginner days floor at 4, Intermediate and
    Advanced floor at 5, regardless of duration.
    """

    if profile is None:
        profile = {}

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 60

    # ---- safety floors per fitness level ------------------------------
    level = str(profile.get("fitness_level", "Intermediate")).lower()
    if level == "beginner":
        floor, ceiling = 4, 8
    elif level == "advanced":
        floor, ceiling = 5, 10
    else:  # intermediate (default)
        floor, ceiling = 5, 9

    # ---- days_per_week frequency budget adjustment --------------------
    try:
        days = int(profile.get("days_per_week", 3))
    except (TypeError, ValueError):
        days = 3

    if days <= 2:
        # very low frequency — cover full body each day means need more
        freq_bonus = 1
    elif days >= 6:
        # high frequency (Push/Pull/Legs × 2) — reuse muscle groups, fewer lifts/day
        freq_bonus = -1
    else:
        freq_bonus = 0

    # ---- style / goal time-per-lift estimate --------------------------
    style = str(profile.get("workout_style", "")).lower()
    goal = str(profile.get("fitness_goal", "")).lower()
    if any(token in style or token in goal for token in ["conditioning", "cardio", "endurance", "fat"]):
        minutes_per_exercise = 6
    elif any(token in style or token in goal for token in ["strength", "power", "powerlifting", "olympic"]):
        minutes_per_exercise = 11
    else:  # hypertrophy / mixed (default)
        minutes_per_exercise = 9

    # Subtract warmup + cooldown from available time first
    usable = max(duration - 15, 15)  # at least 15 effective minutes
    budget_raw = int(round(usable / minutes_per_exercise)) + freq_bonus
    budget = max(floor, min(ceiling, budget_raw))
    return budget


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
            exercise.get(
                "equipment",
                "",
            )
        )

        if (
            available_equipment
            and "no equipment" not in available_equipment
            and exercise_equipment
            and exercise_equipment not in available_equipment
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
        and movement_pattern not in used_patterns
    ):
        score += 5

    if exercise_name in used_exercises:
        score -= 20

    return score


def select_exercises(
    profile,
    target_areas,
    exercise_count,
    used_exercises,
    used_patterns,
    exercise_database,
):
    """Pick ``exercise_count`` exercises for one day of the plan.

    3-phase selection, each phase is strictly score-sorted (higher score
    = better match to profile + target areas):

    1. **Coverage phase** — first ensure *every area* in
       ``target_areas`` that is realistically coverable gets at least 1
       exercise picked.  No Legs day should ever end up with 6 Quads
       exercises and 0 Hams / Glutes.

    2. **Diversity phase** — fill up to ``exercise_count`` using name
       + movement-pattern uniqueness rules.  Name reuse is controlled by
       the external ``used_exercises`` set (caller decides whether it's
       per-week or per distinct split day); movement pattern uniqueness
       lives in ``used_patterns`` which is per-day so Pull Day gets 1x
       horizontal pull + 1x vertical pull + 1x row + 1x bicep curl
       instead of burning all slots on just one pattern early.

    3. **Fill phase** — if budget is still short, relax pattern / name
       uniqueness rules and fill with remaining highest-score
       candidates.  This is the safety net so the function never
       returns 3 exercises for a 90-min 7-lift budget just because
       coverage ran out of unique patterns.
    """

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

    def _add(exercise):
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

        selected.append(exercise)

        if exercise_name:
            used_exercises.add(exercise_name)

        if movement_pattern:
            used_patterns.add(movement_pattern)

    # --- (1) Coverage phase: 1 exercise per unique target area ---------
    # Filter target_areas to *muscle* areas only (exclude sentinels).
    # ``Full Body`` day has 10 areas in ``MUSCLE_AREAS``; if budget is 7
    # we still hit the 7 most common (Chest, Back, Legs/Quads, Shoulders,
    # Biceps, Triceps, Core) via score sort since the scorer boosts
    # primary_muscle matches.
    needed_areas = [
        a for a in target_areas
        if a not in {"Full Body", "Upper Body", "Lower Body", "Legs"}
    ]
    if not needed_areas:
        # e.g. "Legs" fallback: use the real list from MUSCLE_AREAS
        needed_areas = [
            a for a in MUSCLE_AREAS.get("Lower Body", [])
            if a not in {"Lower Body", "Legs"}
        ]

    already_covered: set[str] = set()
    for area in needed_areas:
        if len(selected) >= exercise_count:
            break
        area_norm = normalize_text(area)
        if area_norm in already_covered:
            continue
        for _, exercise in scored:
            exercise_name = normalize_text(exercise.get("name", ""))
            movement_pattern = normalize_text(exercise.get("movement_pattern", ""))
            if exercise in selected:
                continue
            if exercise_name in used_exercises:
                continue
            if movement_pattern and movement_pattern in used_patterns:
                continue
            primary = normalize_text(exercise.get("primary_muscle", ""))
            secondaries = {
                normalize_text(m) for m in exercise.get("secondary_muscles", []) or []
            }
            if area_norm == primary or area_norm in secondaries:
                _add(exercise)
                already_covered.add(area_norm)
                break

    # --- (2) Balance phase: round-robin fill remaining slots across areas --
    # Coverage guarantees 1 per needed area; if budget is much larger than
    # area count (e.g. 8 budget, 2 areas = Chest+Triceps) we want to spread
    # the remaining 6 slots proportionally (~4 Chest / ~2 Triceps), not
    # dump 6 into one area because score-sort favored Triceps.
    if len(selected) < exercise_count and len(needed_areas) >= 1:
        # Pre-build per-area sorted candidate queues so each round of the
        # round-robin can pop the highest-score un-picked candidate for
        # that area.
        per_area_candidates: dict[str, list[tuple[int, Any]]] = {}
        for area_norm in {normalize_text(a) for a in needed_areas}:
            queue: list[tuple[int, Any]] = []
            for score, exercise in scored:
                exercise_name = normalize_text(exercise.get("name", ""))
                movement_pattern = normalize_text(exercise.get("movement_pattern", ""))
                if exercise in selected:
                    continue
                if exercise_name in used_exercises:
                    continue
                if movement_pattern and movement_pattern in used_patterns:
                    continue
                primary = normalize_text(exercise.get("primary_muscle", ""))
                secondaries = {
                    normalize_text(m) for m in exercise.get("secondary_muscles", []) or []
                }
                if area_norm == primary or area_norm in secondaries:
                    queue.append((score, exercise))
            # highest score first (stable — we rely on this for tiebreaks)
            queue.sort(key=lambda t: t[0], reverse=True)
            per_area_candidates[area_norm] = queue

        # Round-robin walk area list, skipping areas whose queue is empty.
        # Prioritize LARGER compound target muscle groups at the FRONT of
        # the cycle so they always get more total lifts than small
        # isolations (e.g. Legs day should be Quads > Hams > Glutes, never
        # Hams > Glutes > Quads).
        COMPOUND_PRIORITY = [
            "chest",
            "back",
            "quadriceps",
            "hamstrings",
            "glutes",
            "legs",
            "shoulders",
            "trapezius",
            "calves",
            "biceps",
            "triceps",
            "core",
        ]
        prio_map = {name: i for i, name in enumerate(COMPOUND_PRIORITY)}
        default_prio = len(COMPOUND_PRIORITY)
        unique_areas = sorted(
            {normalize_text(a) for a in needed_areas},
            key=lambda n: prio_map.get(n, default_prio),
        )
        area_cycle = unique_areas
        cycle_i = 0
        safety = 0
        while len(selected) < exercise_count and safety < 1000:
            safety += 1
            area_norm = area_cycle[cycle_i % len(area_cycle)]
            cycle_i += 1
            q = per_area_candidates.get(area_norm) or []
            advanced = False
            while q:
                score, candidate = q.pop(0)
                exercise_name = normalize_text(candidate.get("name", ""))
                movement_pattern = normalize_text(candidate.get("movement_pattern", ""))
                if candidate in selected:
                    continue
                if exercise_name in used_exercises:
                    continue
                if movement_pattern and movement_pattern in used_patterns:
                    continue
                _add(candidate)
                advanced = True
                break
            if not advanced and sum((len(v) for v in per_area_candidates.values()), 0) == 0:
                break

    # --- (3) Diversity phase: fill to budget with high-score picks -----
    for _, exercise in scored:
        if len(selected) >= exercise_count:
            break
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

        if exercise in selected:
            continue
        if exercise_name in used_exercises:
            continue
        if movement_pattern and movement_pattern in used_patterns:
            continue

        _add(exercise)

    # --- (4) Fill phase: relax uniqueness if budget not yet met ---------
    if len(selected) < exercise_count:
        for _, exercise in scored:
            if len(selected) >= exercise_count:
                break
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

            if exercise in selected:
                continue
            # Allow repeat of movement patterns if needed (e.g. two rows
            # on Pull Day if budget > number of distinct patterns).
            if exercise_name in used_exercises:
                # but NEVER repeat the exact same exercise name in the
                # same day — that's wasteful
                continue

            _add(exercise)

    return selected


def generate_workout_day(
    profile,
    day_number,
    day_name,
    used_exercises,
    exercise_database,
):
    """Generate a single day of training.

    Uniqueness rules (controlled by the caller):
      * ``used_exercises`` tracks names that the caller wants to keep
        globally for the week.  For re-used split days (4-day Upper/Lower repeat)
        this set is reset by split-day bucket, not global.

    Movement-pattern uniqueness is ALWAYS per-day LOCAL so each day gets
    varied stimulus (1x Squat + 1x Hip Hinge + 1x Lunge etc).
    """

    duration = int(
        profile.get(
            "workout_duration",
            profile.get(
                "workout_duration_minutes",
                60,
            ),
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

    sets, reps, rest = get_training_parameters(
        goal,
        style,
        level,
    )

    exercise_count = get_exercise_count(
        duration,
        profile,
    )

    target_areas = MUSCLE_AREAS.get(
        day_name,
        ["Full Body"],
    )

    # Movement pattern dedup is LOCAL to this day only.  Shared across the
    # whole week it would strip 6-day Push day2 day  -3 lifts total of days would be half-empty after day3
    day_patterns: set[str] = set()

    selected_exercises = select_exercises(
        profile,
        target_areas,
        exercise_count,
        used_exercises,
        day_patterns,
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

        exercises.append(exercise_data)

    return {
        "day": day_number,
        "name": day_name,
        "duration": duration,
        "intensity": intensity,
        "warmup": "5-10 minutes",
        "cooldown": "5 minutes",
        "exercises": exercises,
    }


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

    # ------------------------------------------------------------------
    # Exercise-name uniqueness: tracked *per distinct split bucket*
    # rather than globally across the entire week.
    #
    # Why?  The previous implementation used one big ``used_exercises =
    # set()`` for the whole 5-day week.  By day 3 there were only ~3
    # unused names left, so select_exercises couldn't fill a 7-lift
    # 90-min budget and you ended up seeing "3 exercises" on some days.
    #
    # With bucketed tracking:
    #   * 5-day Chest+Triceps / Back+Biceps / Legs / Shoulders+Core /
    #     Full Body → 5 *separate* buckets.  Each day gets the whole
    #     candidate pool; Chest day picks 7 good chest/tricep lifts
    #     without being blocked by a Back exercise used 2 days earlier.
    #   * 4-day Upper / Lower / Upper / Lower → 2 buckets.  Both Upper
    #     days share the same bucket so day1 Bench Press doesn't repeat
    #     on day3 (no redundant volume within the same split group),
    #     but Chest & Back are both free to pick all their good names.
    #   * 6-day Push / Pull / Legs / Push / Pull / Legs → 3 buckets.
    # ------------------------------------------------------------------
    from collections import defaultdict

    used_exercises_by_split: dict[str, set[str]] = defaultdict(set)

    weekly_plan = []

    for day_number, day_name in enumerate(
        split,
        start=1,
    ):
        bucket = day_name  # e.g. "Upper Body", "Chest & Triceps", …
        used_for_bucket = used_exercises_by_split[bucket]
        workout_day = generate_workout_day(
            profile,
            day_number,
            day_name,
            used_for_bucket,
            exercise_database,
        )

        weekly_plan.append(
            workout_day
        )

    return weekly_plan


