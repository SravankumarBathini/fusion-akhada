import json
import streamlit as st
from google import genai
from google.genai import types
import os

def _get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    except Exception as e:
        st.error(f"? AI GENERATION ENGINE CRASHED: {str(e)}")
        return os.getenv("GEMINI_API_KEY")

@st.cache_data(ttl=3600, show_spinner="Connecting to Akhada Cloud... Crafting your custom Hybrid Western & Traditional Indian Vyayam split...")
def generate_weekly_plan(_profile, exercise_database=None):
    api_key = _get_api_key()
    days_per_week = int(_profile.get("days_per_week", 3))
    workout_style = _profile.get("workout_style", "Mixed Training")
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

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an elite master strength coach specializing in Hybrid Functional Training. Your unique expertise seamlessly blends modern Western hypertrophy/strength concepts with traditional Indian physical culture (Vyayam training patterns from ancient Akhadas).
    
    Days per week: {days_per_week} days
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

    For EACH split day, provide a unique selection of 4 to 5 highly distinct exercises. Do not repeat identical movements across days.
    
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
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"? AI GENERATION ENGINE CRASHED: {str(e)}")
        # Secure structural fallback logic rows if JSON token structures ever hit anomalies
        weekly_plan = []
        for i, d_name in enumerate(target_split, start=1):
            weekly_plan.append({
                "day": i, "name": f"Hybrid {d_name} Split", "duration": duration, "intensity": intensity, "warmup": "5 mins", "cooldown": "5 mins",
                "exercises": [
                    {"name": "Traditional Sadha Dand", "equipment": "Bodyweight", "sets": 3, "reps": "12", "rest": "60s", "primary_muscle": "Chest", "movement_pattern": "Compound Push", "instructions": "Deep arching fluid pushups."},
                    {"name": "Dumbbell Floor Press", "equipment": "Dumbbells", "sets": 3, "reps": "12", "rest": "60s", "primary_muscle": "Chest", "movement_pattern": "Horizontal Push", "instructions": ""},
                    {"name": "Wrestler Sapate", "equipment": "Bodyweight", "sets": 3, "reps": "10", "rest": "60s", "primary_muscle": "Full Body", "movement_pattern": "Explosive conditioning", "instructions": "Fluid combo of squats and dands."}
                ]
            })
        return weekly_plan

def normalize_workout_plan(plan):
    if not isinstance(plan, list): return []
    return plan
