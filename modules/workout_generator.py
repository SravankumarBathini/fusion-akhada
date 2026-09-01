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

def generate_weekly_plan(profile, exercise_database=None):
    api_key = _get_api_key()
    days_per_week = int(profile.get("days_per_week", 3))
    workout_style = profile.get("workout_style", "Mixed Training")
    fitness_goal = profile.get("fitness_goal", "General Fitness")
    fitness_level = profile.get("fitness_level", "Beginner")
    duration = profile.get("workout_duration", 45)
    intensity = profile.get("workout_intensity", "Moderate")
    equipment = profile.get("equipment", ["No equipment"])
    injury = profile.get("physical_injuries", "None disclosed")
    avoid = profile.get("exercises_to_avoid", "None")

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
    You are an elite personal fitness trainer. Create a highly customized, full-variety weekly training routine.
    Days per week: {days_per_week} days
    Workout Style: {workout_style}
    Fitness Goal: {fitness_goal}
    Target Split Routine: {target_split}
    Available Equipment: {equipment}

    CRITICAL HEALTH & SAFETY LIMITATIONS:
    The user has recorded this medical/injury background: "{injury}". Stated exercises to avoid: "{avoid}".
    You must carefully select exercises that place ZERO structural stress on the injured zone. If neck surgery or upper back issues are present, absolutely avoid any heavy overhead loads, trap-intensive movements, or cervical spine loading. Focus instead on chest-supported machine rows, dumbbells down at your sides, or floor presses.

    For EACH split day, provide a unique selection of 4 to 5 highly distinct, real-world exercises. Do not repeat the same dummy titles across days.
    
    Return a valid JSON list containing exactly {days_per_week} distinct day objects following this structure:
    [
      {{
        "day": 1,
        "name": "Workout Day Name",
        "duration": {duration},
        "intensity": "{intensity}",
        "warmup": "5-10 minutes",
        "cooldown": "5 minutes",
        "exercises": [
          {{
            "name": "Exercise Name",
            "equipment": "Required Equipment",
            "sets": 3,
            "reps": "8-12",
            "rest": "60s",
            "primary_muscle": "Target Muscle Group",
            "movement_pattern": "Movement Direction",
            "instructions": "Brief step-by-step cue description."
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
        weekly_plan = []
        for i, d_name in enumerate(target_split, start=1):
            weekly_plan.append({
                "day": i, "name": d_name, "duration": duration, "intensity": intensity, "warmup": "5 mins", "cooldown": "5 mins",
                "exercises": [
                    {"name": "Dumbbell Floor Press", "equipment": "Dumbbells", "sets": 3, "reps": "12", "rest": "60s", "primary_muscle": "Chest", "movement_pattern": "Horizontal Push", "instructions": ""},
                    {"name": "Glute Bridges", "equipment": "Bodyweight", "sets": 3, "reps": "15", "rest": "60s", "primary_muscle": "Glutes", "movement_pattern": "Hinge", "instructions": ""},
                    {"name": "Bodyweight Air Squats", "equipment": "Bodyweight", "sets": 3, "reps": "12", "rest": "60s", "primary_muscle": "Legs", "movement_pattern": "Squat", "instructions": ""}
                ]
            })
        return weekly_plan

def normalize_workout_plan(plan):
    if not isinstance(plan, list): return []
    return plan
