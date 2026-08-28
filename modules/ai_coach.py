
import os
from typing import Any

import streamlit as st
from google import genai

from modules.analytics import (
    format_training_intelligence,
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_MODEL = "gemini-3.6-flash"


# ============================================================
# GEMINI INITIALIZATION
# ============================================================

def _get_api_key():
    """
    Read Gemini API key from Streamlit secrets first,
    then fall back to environment variables.
    """

    try:
        api_key = st.secrets.get(
            "GEMINI_API_KEY"
        )
    except Exception:
        api_key = None

    if not api_key:
        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured "
            "in Streamlit secrets or environment variables."
        )

    return api_key


def _create_gemini_client():
    """
    Create and return a Gemini API client.
    """

    api_key = _get_api_key()

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# DATA FORMATTERS
# ============================================================

def _format_profile(
    profile: dict[str, Any],
) -> str:

    if not profile:
        return (
            "No profile information available."
        )

    equipment = profile.get(
        "equipment",
        [],
    )

    target_areas = profile.get(
        "target_areas",
        [],
    )

    if not isinstance(
        equipment,
        list,
    ):
        equipment = []

    if not isinstance(
        target_areas,
        list,
    ):
        target_areas = []

    return f"""
Name: {profile.get("name", "Unknown")}
Age: {profile.get("age", "Unknown")}
Gender: {profile.get("gender", "Unknown")}
Height: {profile.get("height", "Unknown")} cm
Weight: {profile.get("weight", "Unknown")} kg

Fitness goal: {profile.get("fitness_goal", "Unknown")}
Fitness level: {profile.get("fitness_level", "Unknown")}
Workout location: {profile.get("workout_location", "Unknown")}

Days per week: {profile.get("days_per_week", "Unknown")}
Workout duration: {profile.get("workout_duration", "Unknown")} minutes

Equipment:
{", ".join(equipment)}

Target areas:
{", ".join(target_areas)}

Workout style:
{profile.get("workout_style", "Unknown")}

Workout intensity:
{profile.get("workout_intensity", "Unknown")}

Exercises the user enjoys:
{profile.get("exercises_enjoy", "None specified")}

Exercises the user wants to avoid:
{profile.get("exercises_to_avoid", "None specified")}
"""


def _format_workout_plan(
    workout_plan,
) -> str:

    if not workout_plan:
        return (
            "No workout plan currently available."
        )

    lines = []

    for workout_day in workout_plan:

        day_number = workout_day.get(
            "day",
            "",
        )

        name = workout_day.get(
            "name",
            "Workout",
        )

        duration = workout_day.get(
            "duration",
            "",
        )

        intensity = workout_day.get(
            "intensity",
            "",
        )

        lines.append(
            f"\nDay {day_number}: {name}"
        )

        lines.append(
            f"Duration: {duration} minutes"
        )

        lines.append(
            f"Intensity: {intensity}"
        )

        for exercise in workout_day.get(
            "exercises",
            [],
        ):

            exercise_name = exercise.get(
                "name",
                "Exercise",
            )

            sets = exercise.get(
                "sets",
                "-",
            )

            reps = exercise.get(
                "reps",
                "-",
            )

            equipment = exercise.get(
                "equipment",
                "-",
            )

            lines.append(
                f"- {exercise_name}: "
                f"{sets} sets x {reps} reps "
                f"({equipment})"
            )

    return "\n".join(lines)


def _format_workout_history(
    workout_history,
) -> str:

    if not workout_history:
        return (
            "No completed workouts have "
            "been logged yet."
        )

    lines = []

    recent_history = workout_history[-20:]

    for workout in recent_history:

        date = workout.get(
            "date",
            "Unknown date",
        )

        workout_name = workout.get(
            "workout_name",
            "Workout",
        )

        duration = workout.get(
            "actual_duration",
            "-",
        )

        total_sets = workout.get(
            "total_sets",
            0,
        )

        total_volume = workout.get(
            "total_volume",
            0,
        )

        lines.append(
            f"\n{date} — {workout_name}"
        )

        lines.append(
            f"Duration: {duration} minutes"
        )

        lines.append(
            f"Completed sets: {total_sets}"
        )

        lines.append(
            f"Total volume: {total_volume} kg"
        )

        for exercise in workout.get(
            "exercises",
            [],
        ):

            exercise_name = exercise.get(
                "name",
                "Exercise",
            )

            completed = exercise.get(
                "completed",
                False,
            )

            status = (
                "Completed"
                if completed
                else "Not completed"
            )

            lines.append(
                f"  {exercise_name}: {status}"
            )

            for set_data in exercise.get(
                "sets",
                [],
            ):

                if not set_data.get(
                    "completed",
                    False,
                ):
                    continue

                weight = set_data.get(
                    "weight_kg",
                    0,
                )

                reps = set_data.get(
                    "actual_reps",
                    0,
                )

                volume = set_data.get(
                    "volume",
                    0,
                )

                lines.append(
                    f"    Set "
                    f"{set_data.get('set_number', '-')}: "
                    f"{weight} kg x "
                    f"{reps} reps "
                    f"= {volume} kg volume"
                )

    return "\n".join(lines)


# ============================================================
# SYSTEM PROMPT
# ============================================================

def _build_system_prompt(
    profile,
    workout_plan,
    workout_history,
):

    training_intelligence = (
        format_training_intelligence(
            workout_history
        )
    )

    return f"""
You are the personal AI workout coach inside a workout
tracking application.

Your job is to provide practical, personalized,
evidence-informed training guidance using:

1. The user's profile.
2. The current workout plan.
3. Logged workout history.
4. Calculated training intelligence.

IMPORTANT RULES:

1. Use actual user data whenever possible.
2. Never invent weights, reps, workouts, PRs,
   or historical events.
3. If information is unavailable, say so.
4. Respect available equipment.
5. Respect exercises the user wants to avoid.
6. Consider the user's fitness goal and experience.
7. Use progressive overload appropriately.
8. Consider recent training and recovery.
9. Do not make major programming changes based
   on one isolated session.
10. Distinguish facts from coaching recommendations.
11. Prefer actionable recommendations.
12. Do not diagnose medical conditions.
13. For significant pain, injury symptoms,
    chest pain, dizziness, or other concerning
    symptoms, recommend appropriate medical
    evaluation.
14. Never claim to have observed exercise form.
15. Never pretend the data says something it does not.
16. Do not automatically change the user's workout plan.
17. When recommending progression, explain exactly
    what should change and why.

TRAINING INTELLIGENCE RULE:

Use the calculated training intelligence as a
high-level summary of the user's actual data.

Do not blindly interpret a positive or negative
volume change as good or bad. Consider context,
training frequency, exercise selection, goal,
and recent sessions.

COACHING STYLE:

- Clear
- Practical
- Specific
- Training-focused
- Encouraging without excessive praise
- Concise enough for an application
- Use headings and bullets when useful

USER PROFILE:
{_format_profile(profile)}

CURRENT WORKOUT PLAN:
{_format_workout_plan(workout_plan)}

TRAINING INTELLIGENCE:
{training_intelligence}

RECENT RAW WORKOUT HISTORY:
{_format_workout_history(workout_history)}
"""


# ============================================================
# AI COACH
# ============================================================

def ask_ai_coach(
    question,
    profile,
    workout_plan,
    workout_history,
):

    if not question or not question.strip():
        raise ValueError(
            "Please enter a question."
        )

    client = _create_gemini_client()

    system_prompt = _build_system_prompt(
        profile,
        workout_plan,
        workout_history,
    )

    user_prompt = f"""
USER'S QUESTION:

{question.strip()}

Answer the user's question directly.

Use the user's training intelligence and history
when relevant.

Do not repeat the entire profile, plan, or history.

If recommending a change, make it specific and
practical.

If the available data is insufficient to make a
strong recommendation, say what additional data
would help.
"""

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=user_prompt,
        system_instruction=system_prompt,
    )

    answer = getattr(
        interaction,
        "output_text",
        None,
    )

    if not answer:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return answer.strip()

