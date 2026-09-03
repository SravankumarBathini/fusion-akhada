import json
import logging
import time
import streamlit as st
from google import genai
from google.genai import types
import os

from domain.workout_validation import has_duplicate_exercises

logger = logging.getLogger(__name__)


def normalize_workout_plan(plan):
    """Preserve the AI generator's historical pass-through contract."""

    return plan if isinstance(plan, list) else []

def _get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    except Exception as e:
        st.error(f"AI GENERATION ENGINE CRASHED: {str(e)}")
        return os.getenv("GEMINI_API_KEY")

def generate_weekly_plan(_profile, exercise_database=None):
    api_key = _get_api_key()
    days_per_week = int(_profile.get("days_per_week", 3))
    workout_style = _profile.get("workout_style", "Mixed Training")
    program_preset = _profile.get("program_preset", "Custom")
    fitness_goal = _profile.get("fitness_goal", "General Fitness")
    fitness_level = _profile.get("fitness_level", "Beginner")
    duration = _profile.get("workout_duration", 45)
    intensity = _profile.get("workout_intensity", "Moderate")
    equipment = _profile.get("equipment", ["No equipment"])
    injury = _profile.get("physical_injuries") or _profile.get("injuries_and_limitations") or "None disclosed"
    avoid = _profile.get("exercises_to_avoid", "None")

    splits = {
        1: ["Full Body"],
        2: ["Full Body", "Full Body"],
        3: ["Full Body", "Upper Body", "Lower Body"],
        4: ["Upper Body", "Lower Body", "Upper Body", "Lower Body"],
        5: ["Chest & Triceps", "Back & Biceps", "Legs", "Shoulders & Core", "Full Body"],
        6: ["Chest & Triceps", "Back & Biceps", "Legs", "Shoulders", "Arms & Core", "Full Body"],
        7: ["Upper Body", "Lower Body", "Upper Body", "Lower Body", "Upper Body", "Lower Body", "Full Body"]
    }
    target_split = splits.get(days_per_week, splits)

    if not api_key:
        return []

    client = _get_gemini_client(api_key)
    
    prompt = f"""
    You are an elite master strength coach specializing in Hybrid Functional Training. Your unique expertise seamlessly blends modern Western hypertrophy/strength concepts with traditional Indian physical culture (Vyayam training patterns from ancient Akhadas).
    
    Days per week: {days_per_week} days
    Program Preset: {program_preset}
    Workout Style: {workout_style} (Hybrid Western & Indian Traditional)
    Fitness Goal: {fitness_goal}
    Target Split Routine: {target_split}
    Available Equipment: {equipment}

    CRITICAL GYMNASTIC & CULTURAL TRAINING RULES:
    1. You MUST intentionally weave a beautiful blend of both modern Western training and traditional Indian movements into every single day's routine.
    2. Incorporate traditional bodyweight and equipment-free variations natively:
       - Different types of Dands: Sadha Dand, Hanuman Dand (for core/hip mobility), Ram Murti Dand (isometric/dynamic push), or Hindu Push-Ups.
       - Sapate (Traditional Indian wrestler burpees combining squat, dand, and jump for explosive conditioning).
       - Bethaks (Traditional deep squats) or Hanuman Bethaks.
       - Spine Push Boards / Gymnastic blocks if applicable.
    3. If the user lists heavy tools like "Mudgar", "Clubbells", "Mace", or "Gada" in their available equipment parameters, actively suggest rotational core movements like Gada 360 Swings, Mudgar rotations, or club patterns. If they only have dumbbells, adapt the dands/sapate movements natively!
    
    CRITICAL HEALTH & SAFETY LIMITATIONS:
    The user has recorded this medical/injury background: "{injury}". Stated exercises to avoid: "{avoid}".
    You must carefully select exercises that place ZERO structural stress on the injured zone. If neck surgery, cervical strain, or shoulder impingement is present, carefully adapt or substitute overhead Gada swings or extreme twisting dands. Ensure spinal alignment remains neutral.

    MANDATORY EXERCISE VARIABILITY: You MUST generate radically distinct exercises for every training day based on that day's target split name in the Target Split Routine. It is strictly forbidden to repeat an exercise, movement, or exercise variation across different days. Do not reuse an exercise even when the same split type appears more than once; every day must have its own completely different exercise selection.
    For EACH split day, provide a unique selection of 4 to 5 highly distinct exercises that directly matches that day's target split.
    
    Return a valid JSON list containing exactly {days_per_week} distinct day objects following this structural schema format:
    [
      {{
        "day": 1,
        "name": "Workout Day Name (e.g. Akhada Upper Body Strength)",
        "duration": {duration},
        "intensity": "{intensity}",
        "warmup": "5-10 minutes mobility",
        "cooldown": "5 minutes stretching",
        "exercises": [
          {{
            "name": "Exercise Name (e.g. Hanuman Dand)",
            "equipment": "Bodyweight",
            "sets": 3,
            "reps": "8-12",
            "rest": "60s",
            "primary_muscle": "Chest & Shoulders",
            "movement_pattern": "Compound Push",
            "instructions": "Flow from downward dog into a deep sweeping push-up, bringing one leg forward dynamically."
          }}
        ]
      }}
    ]
    """

    try:
        started_at = time.perf_counter()
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=3000,
            )
        )
        logger.info(
            "Workout plan generation completed in %.2fs",
            time.perf_counter() - started_at,
        )
        generated_plan = json.loads(response.text)
        exercise_names = set()
        for day in generated_plan:
            for generated_exercise in day.get("exercises", []):
                exercise_name = generated_exercise.get("name", "").strip().casefold()
                if exercise_name in exercise_names:
                    raise ValueError(
                        "Gemini returned an exercise repeated across training days."
                    )
                if exercise_name:
                    exercise_names.add(exercise_name)
        return generated_plan
    except Exception as e:
        st.error(f"AI GENERATION ENGINE CRASHED: {str(e)}")
        # Secure structural fallback logic if JSON token structures ever hit anomalies.
        def exercise(name, equipment, primary_muscle, movement_pattern, instructions, reps="12"):
            return {
                "name": name, "equipment": equipment, "sets": 3, "reps": reps,
                "rest": "60s", "primary_muscle": primary_muscle,
                "movement_pattern": movement_pattern, "instructions": instructions
            }

        fallback_exercises = {
            "push": [
                exercise("Hanuman Dand", "Bodyweight", "Chest & Shoulders", "Compound Push", "Flow from downward dog into a deep sweeping push-up."),
                exercise("Dumbbell Floor Press", "Dumbbells", "Chest", "Horizontal Push", "Press dumbbells upward while keeping the shoulders packed."),
                exercise("Pike Push-Up", "Bodyweight", "Shoulders", "Vertical Push", "Lower the crown of the head between the hands with controlled tempo.")
            ],
            "push_variant": [
                exercise("Ram Murti Dand", "Bodyweight", "Chest & Triceps", "Compound Push", "Use a slow isometric pause at the bottom of each flowing push-up."),
                exercise("Single-Arm Dumbbell Press", "Dumbbells", "Chest", "Unilateral Push", "Press one dumbbell from the floor while bracing the opposite side."),
                exercise("Close-Grip Push-Up", "Bodyweight", "Triceps", "Horizontal Push", "Keep the elbows close to the ribs throughout each repetition.")
            ],
            "pull": [
                exercise("Inverted Row", "Bodyweight", "Back", "Horizontal Pull", "Pull the chest toward a secure bar or table edge while keeping the body straight."),
                exercise("Dumbbell Bent-Over Row", "Dumbbells", "Back", "Horizontal Pull", "Row toward the hips with a neutral spine."),
                exercise("Band Face Pull", "Resistance Band", "Rear Delts", "Horizontal Pull", "Pull the band toward the face and rotate the hands outward.")
            ],
            "pull_variant": [
                exercise("Towel Door Row", "Towel", "Upper Back", "Horizontal Pull", "Brace the feet and row against a securely anchored towel."),
                exercise("Renegade Row", "Dumbbells", "Back & Core", "Unilateral Pull", "Alternate rows from a stable plank position."),
                exercise("Dumbbell Pullover", "Dumbbell", "Lats", "Shoulder Extension", "Lower one dumbbell behind the head and pull it back over the chest.")
            ],
            "legs": [
                exercise("Bethak", "Bodyweight", "Quadriceps", "Squat", "Perform a deep traditional squat with an upright torso."),
                exercise("Dumbbell Romanian Deadlift", "Dumbbells", "Hamstrings", "Hip Hinge", "Hinge at the hips while keeping the dumbbells close to the legs."),
                exercise("Reverse Lunge", "Bodyweight", "Glutes & Legs", "Unilateral Squat", "Step back softly and drive through the front foot.")
            ],
            "legs_variant": [
                exercise("Hanuman Bethak", "Bodyweight", "Legs", "Dynamic Squat", "Alternate a deep squat with a controlled forward-reaching step."),
                exercise("Goblet Squat", "Dumbbell", "Quadriceps", "Squat", "Hold the weight at the chest and squat below parallel as mobility allows."),
                exercise("Single-Leg Glute Bridge", "Bodyweight", "Glutes", "Hip Extension", "Drive the hips upward while keeping the pelvis level.")
            ],
            "legs_variant_2": [
                exercise("Cossack Squat", "Bodyweight", "Adductors & Glutes", "Lateral Squat", "Shift into one hip while extending the opposite leg to the side."),
                exercise("Dumbbell Step-Up", "Dumbbell", "Quadriceps & Glutes", "Unilateral Step", "Step onto a stable platform and stand tall through the leading leg."),
                exercise("Standing Calf Raise", "Bodyweight", "Calves", "Plantar Flexion", "Rise onto the balls of the feet and lower slowly.")
            ],
            "shoulders_core": [
                exercise("Dumbbell Arnold Press", "Dumbbells", "Shoulders", "Vertical Push", "Rotate the palms as the weights travel from chest height to overhead."),
                exercise("Lateral Raise", "Dumbbells", "Side Delts", "Shoulder Abduction", "Raise the weights to shoulder height without shrugging."),
                exercise("Dead Bug", "Bodyweight", "Core", "Anti-Extension", "Brace the abdomen while slowly extending opposite limbs.")
            ],
            "shoulders": [
                exercise("Dumbbell Push Press", "Dumbbells", "Shoulders", "Explosive Push", "Use a shallow leg drive to press the weights overhead."),
                exercise("Bent-Over Reverse Fly", "Dumbbells", "Rear Delts", "Horizontal Pull", "Open the arms wide with a stable, flat back."),
                exercise("Bear Plank Shoulder Tap", "Bodyweight", "Shoulders & Core", "Anti-Rotation", "Tap opposite shoulders from a low bear-plank position.")
            ],
            "arms_core": [
                exercise("Alternating Dumbbell Curl", "Dumbbells", "Biceps", "Elbow Flexion", "Curl one weight at a time without swinging."),
                exercise("Overhead Triceps Extension", "Dumbbell", "Triceps", "Elbow Extension", "Lower the weight behind the head while keeping elbows pointed forward."),
                exercise("Mountain Climber", "Bodyweight", "Core", "Dynamic Conditioning", "Drive alternating knees toward the chest from a strong plank.")
            ],
            "full_body": [
                exercise("Wrestler Sapate", "Bodyweight", "Full Body", "Explosive Conditioning", "Flow through a squat, dand, and jump."),
                exercise("Dumbbell Thruster", "Dumbbells", "Full Body", "Squat to Push", "Stand from a front squat and finish with a controlled press."),
                exercise("Bear Crawl", "Bodyweight", "Full Body", "Locomotion", "Move forward slowly while keeping the knees close to the floor.")
            ],
            "full_body_variant": [
                exercise("Hindu Push-Up to Squat", "Bodyweight", "Full Body", "Compound Conditioning", "Flow from a push-up into a deep squat without losing control."),
                exercise("Dumbbell Clean", "Dumbbells", "Full Body", "Olympic Pull", "Drive through the hips to bring the dumbbells to the shoulders."),
                exercise("Walking Lunge with Twist", "Bodyweight", "Full Body", "Rotational Lunge", "Step forward and rotate gently over the lead leg.")
            ]
        }

        weekly_plan = []
        for i, d_name in enumerate(target_split, start=1):
            split_name = d_name.lower()
            if "chest" in split_name or "triceps" in split_name or "push" in split_name:
                exercise_key = "push_variant" if i % 2 == 0 else "push"
            elif "back" in split_name or "biceps" in split_name or "pull" in split_name:
                exercise_key = "pull_variant" if i % 2 == 0 else "pull"
            elif "leg" in split_name or "lower" in split_name:
                leg_variants = ["legs", "legs_variant", "legs_variant_2"]
                exercise_key = leg_variants[((i - 1) // 2) % len(leg_variants)]
            elif "shoulder" in split_name and "core" in split_name:
                exercise_key = "shoulders_core"
            elif "shoulder" in split_name:
                exercise_key = "shoulders"
            elif "arm" in split_name or "core" in split_name:
                exercise_key = "arms_core"
            elif "upper" in split_name:
                upper_body_variants = ["push", "pull", "push_variant", "pull_variant"]
                exercise_key = upper_body_variants[((i - 1) // 2) % len(upper_body_variants)]
            else:
                exercise_key = "full_body_variant" if i % 2 == 0 else "full_body"

            weekly_plan.append({
                "day": i, "name": f"Hybrid {d_name} Split", "duration": duration, "intensity": intensity, "warmup": "5 mins", "cooldown": "5 mins",
                "exercises": fallback_exercises[exercise_key]
            })
        return weekly_plan


@st.cache_resource(show_spinner=False)
def _get_gemini_client(api_key):
    """Reuse the Gemini client across Streamlit reruns."""
    return genai.Client(api_key=api_key)
