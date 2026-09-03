from datetime import datetime, timedelta


def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            normalize_text(item)
            for item in value
        )

    return str(value).strip().lower()


def exercise_is_avoided(exercise, avoided_exercises):
    exercise_name = normalize_text(
        exercise.get("name", "")
    )

    avoided_text = normalize_text(
        avoided_exercises
    )

    if not avoided_text:
        return False

    return exercise_name in avoided_text


def exercise_is_preferred(exercise, preferred_exercises):
    exercise_name = normalize_text(
        exercise.get("name", "")
    )

    preferred_text = normalize_text(
        preferred_exercises
    )

    if not preferred_text:
        return False

    return exercise_name in preferred_text


def get_exercise_instruction(exercise):
    """Return coach guidance even when a generated plan omits instructions."""
    instructions = str(exercise.get("instructions", "")).strip()
    if instructions:
        return instructions

    pattern = normalize_text(exercise.get("movement_pattern", ""))
    guidance = {
        "squat": "Keep your chest tall, brace your core, and lower under control. Drive through your whole foot to stand.",
        "lunge": "Step into a stable stance, lower with control, and keep the front knee tracking over the toes.",
        "horizontal push": "Brace your core, keep your shoulders packed, and press smoothly without flaring your elbows.",
        "vertical push": "Keep your ribs down, brace your core, and press through a controlled range without shrugging.",
        "horizontal pull": "Keep a neutral spine, pull your elbows toward your ribs, and pause when your shoulder blades come together.",
        "vertical pull": "Start with your shoulders down, pull your elbows toward your sides, and lower slowly.",
        "hip hinge": "Push your hips back with a neutral spine, keep the load close, and squeeze your glutes to stand.",
    }
    return guidance.get(
        pattern,
        "Move slowly and with control. Keep your spine neutral, breathe steadily, and stop if you feel sharp pain.",
    )


def get_exercise_coaching(exercise):
    """Return practical beginner coaching for the exercise movement pattern."""
    pattern = normalize_text(exercise.get("movement_pattern", ""))
    coaching = {
        "squat": {
            "steps": [
                "Stand with feet about shoulder-width apart.",
                "Brace your core and lower by sending your hips back and down.",
                "Keep your knees tracking with your toes, then drive through your feet to stand.",
            ],
            "breathing": "Inhale as you lower; exhale as you stand.",
            "mistakes": "Knees collapsing inward, heels lifting, or rushing the bottom position.",
            "modification": "Use a chair or reduce depth until you can keep control.",
            "progression": "Add light load or a three-second lowering phase.",
        },
        "lunge": {
            "steps": [
                "Stand tall and step one foot forward or backward.",
                "Lower both knees under control while keeping your torso upright.",
                "Push through the whole front foot to return to the start.",
            ],
            "breathing": "Inhale as you lower; exhale as you return.",
            "mistakes": "Taking an unstable step, letting the front knee cave inward, or bouncing.",
            "modification": "Hold a wall for balance or use a shorter range of motion.",
            "progression": "Add dumbbells or pause briefly at the bottom.",
        },
        "horizontal push": {
            "steps": [
                "Set your hands under your shoulders and brace your body.",
                "Lower your chest with elbows angled slightly toward your ribs.",
                "Press the floor away and finish with your shoulders stable.",
            ],
            "breathing": "Inhale as you lower; exhale as you press.",
            "mistakes": "Hips sagging, elbows flaring, or shoulders shrugging.",
            "modification": "Perform the movement against a wall or elevated surface.",
            "progression": "Use a slower lowering phase or add a pause near the bottom.",
        },
        "horizontal pull": {
            "steps": [
                "Set your spine neutral and let your arms reach without rounding your back.",
                "Pull your elbows toward your ribs and squeeze your shoulder blades.",
                "Lower the weight slowly until your arms are long again.",
            ],
            "breathing": "Exhale as you pull; inhale as you lower.",
            "mistakes": "Shrugging, twisting, or using momentum to move the weight.",
            "modification": "Use a lighter weight and support one hand on a bench.",
            "progression": "Add a one-second squeeze at the top of each rep.",
        },
        "hip hinge": {
            "steps": [
                "Stand tall with a soft bend in your knees.",
                "Push your hips back while keeping your spine long and the load close.",
                "Drive your hips forward and squeeze your glutes to stand.",
            ],
            "breathing": "Inhale before lowering; exhale as you stand.",
            "mistakes": "Rounding the lower back, squatting instead of hinging, or leaning too far.",
            "modification": "Practice with hands sliding down your thighs and no weight.",
            "progression": "Increase load gradually while keeping the same controlled hinge.",
        },
    }
    return coaching.get(
        pattern,
        {
            "steps": [
                "Set a stable starting position and brace your core.",
                "Move through a comfortable range with steady control.",
                "Return slowly and reset before the next repetition.",
            ],
            "breathing": "Breathe steadily; avoid holding your breath.",
            "mistakes": "Rushing, using momentum, or losing a neutral spine.",
            "modification": "Reduce the range, load, or speed until the movement feels controlled.",
            "progression": "Add resistance or repetitions only while technique stays consistent.",
        },
    )


def parse_history_datetime(workout):
    date_text = str(
        workout.get(
            "date",
            "",
        )
    ).strip()

    time_text = str(
        workout.get(
            "time",
            "",
        )
    ).strip()

    if not date_text:
        return None

    combined = date_text

    if time_text:
        combined = f"{date_text} {time_text}"

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                combined,
                fmt,
            )
        except ValueError:
            continue

    return None


def get_completed_exercises_count(history):
    total = 0

    for workout in history:
        exercises = workout.get(
            "exercises",
            [],
        )

        for exercise in exercises:
            if exercise.get(
                "completed",
                False,
            ):
                total += 1

    return total


def get_workouts_this_week(history):
    today = datetime.now().date()

    start_of_week = (
        today
        - timedelta(days=today.weekday())
    )

    count = 0

    for workout in history:
        workout_datetime = parse_history_datetime(
            workout
        )

        if workout_datetime is None:
            continue

        if (
            start_of_week
            <= workout_datetime.date()
            <= today
        ):
            count += 1

    return count


def get_workouts_this_month(history):
    today = datetime.now().date()

    count = 0

    for workout in history:
        workout_datetime = parse_history_datetime(
            workout
        )

        if workout_datetime is None:
            continue

        if (
            workout_datetime.year == today.year
            and workout_datetime.month == today.month
        ):
            count += 1

    return count