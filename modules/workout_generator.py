import json
import streamlit as st
from google import genai
import os

def _get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    except Exception:
        return os.getenv("GEMINI_API_KEY")

def generate_weekly_plan(profile, exercise_database=None):
    """
    Generates a 100% full-variety workout plan by querying Gemini directly
    based on user goals, equipment, and injury profiles, avoiding local database starvation.
    """
    api_key = _get_api_key()
    if not api_key:
        # Emergency backup structured array if keys are missing
        return [
            {
                "day": 1, "name": "Chest & Triceps", "duration": 60, "intensity": "Challenging", "warmup": "5 mins", "cooldown": "5 mins",
                "exercises": [{"name": "Push-Ups", "equipment": "Bodyweight", "sets": 3, "reps": "12", "rest": "60s", "primary_muscle": "Chest", "movement_pattern": "Push"}]
            }
        ]

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
    target_split = splits.get(days_per_week, splits[3])

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an elite personal trainer. Generate a personalized weekly workout plan for a {fitness_level} athlete.
    Goal: {fitness_goal}
    Style: {workout_style}
    Target Split Structure: {target_split} (Exactly {days_per_week} training days)
    Available Equipment: {equipment}
    
    CRITICAL HEALTH & SAFETY BOUNDARY:
    The user has specified these physical limitations/injuries: "{injury}". 
    Stated exercises to avoid: "{avoid}".
    You must carefully select exercises that place ZERO strain or direct axial load on the injured zones. If neck surgery or neck pain is noted, absolutely avoid heavy trap loading, overhead presses, or neck strain, and prefer chest-supported or machine lines.

    For EACH day in the target split, provide exactly 4 to 5 unique, safe exercises. Do not leave any days empty.

    Return ONLY a valid JSON list containing exactly {days_per_week} day objects. No markdown, no triple backticks (```json). Follow this exact structural schema format:
    [
      {{
        "day": 1,
        "name": "Chest & Triceps",
        "duration": {duration},
        "intensity": "{intensity}",
        "warmup": "5-10 minutes",
        "cooldown": "5 minutes",
        "exercises": [
          {{
            "name": "Dumbbell Floor Press",
            "equipment": "Dumbbells",
            "sets": 3,
            "reps": "8-12",
            "rest": "60s",
            "primary_muscle": "Chest",
            "movement_pattern": "Horizontal Push",
            "instructions": "Lie flat on the floor and press dumbbells up safely."
          }}
        ]
      }}
    ]
    """

    try:
        response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        parsed_plan = json.loads(clean_text)
        return parsed_plan
    except Exception:
        # Secure structural fallback logic rows if JSON token structures ever hit anomalies
        weekly_plan = []
        for i, d_name in enumerate(target_split, start=1):
            weekly_plan.append({
                "day": i, "name": d_name, "duration": duration, "intensity": intensity, "warmup": "5 mins", "cooldown": "5 mins",
                "exercises": [
                    {"name": f"Safe Bodyweight Movement {idx}", "equipment": "Bodyweight", "sets": 3, "reps": "12", "rest": "60s", "primary_muscle": d_name, "movement_pattern": "Calisthenics"}
                    for idx in range(1, 5)
                ]
            })
        return weekly_plan

def normalize_workout_plan(plan):
    if not isinstance(plan, list): return []
    return plan
