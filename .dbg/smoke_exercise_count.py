import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from domain.workout_generation import generate_weekly_plan, get_exercise_count

# 1. Unit-test the count driver for the user's actual profile:
profile_user = {
    "age": 23,
    "name": "Rohit",
    "gender": "Male",
    "height": 178.0,
    "weight": 75.0,
    "equipment": ["Barbell", "Dumbbell", "Cable", "Machine", "Bodyweight", "Pull-up Bar", "Bench"],
    "fitness_goal": "Build muscle",
    "target_areas": ["Chest", "Back", "Shoulders", "Biceps", "Triceps", "Quadriceps", "Hamstrings", "Glutes", "Core", "Calves", "Trapezius"],
    "days_per_week": 5,
    "fitness_level": "Intermediate",
    "workout_style": "Hypertrophy / Muscle Building",
    "program_preset": "Hybrid Muscle Builder",
    "exercises_enjoy": "Not anything specific ",
    "workout_duration": 90,
    "workout_duration_minutes": 90,
    "workout_location": "Gym",
    "physical_injuries": "NO",
    "workout_intensity": "Challenging",
    "exercises_to_avoid": "NA",
}
print("=== get_exercise_count(profile_user) for 90 min Intermediate 5d Hypertrophy ===")
print(f"  count = {get_exercise_count(profile_user.get('workout_duration', 60), profile_user)} (expected 7 or 8, floor=5 Intermediate)")

# 2. Load exercise catalog via application loader (with fallback = []).
from application import data_loader
from pathlib import Path
root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
exercises_file = root / "data" / "exercises.json"
catalog = data_loader._load_exercise_catalog(exercises_file, _warning_callback=lambda *a, **kw: None)
assert isinstance(catalog, list), f"Expected list catalog, got {type(catalog).__name__}"
print(f"\nExercise catalog size = {len(catalog)}")
if not catalog:
    print("  catalog empty (data/exercises.json missing on disk). Use generate_new_plan from UI.")

# 3. Generate the plan.
if not catalog:
    # Build a minimal fake catalog (150 exercises) so select_exercises has coverage.
    import random as _r
    _r.seed(0)
    areas = ["Chest","Back","Shoulders","Biceps","Triceps","Quadriceps","Hamstrings","Glutes","Core","Calves","Trapezius"]
    pats = ["Horizontal Press","Vertical Press","Horizontal Pull","Vertical Pull","Squat","Hip Hinge","Lunge","Isolation","Carry","Core","Plyometrics"]
    eq = ["Barbell","Dumbbell","Cable","Machine","Bodyweight","Pull-up Bar","Bench"]
    catalog = []
    for i in range(160):
        muscle = _r.choice(areas)
        catalog.append({
            "name": f"Exercise {i+1} ({muscle})",
            "equipment": _r.choice(eq),
            "primary_muscle": muscle,
            "secondary_muscles": _r.sample([m for m in areas if m != muscle], k=_r.randint(1, 2)),
            "movement_pattern": _r.choice(pats),
            "exercise_type": "Strength",
            "difficulty": _r.choice(["Beginner","Intermediate","Advanced"]),
            "instructions": "Sample",
            "target_areas": [muscle],
        })
    print(f"  (built synthetic catalog size={len(catalog)} for smoke)")
plan = generate_weekly_plan(profile_user, catalog)
print(f"\nWeek length = {len(plan)} days (expected 5)")
ok = True
for day in plan:
    day_n = day["day"]
    name = day["name"]
    ex = day.get("exercises", [])
    count = len(ex)
    muscle_counts: dict[str, int] = collections.Counter()
    for e in ex:
        primary = str(e.get("primary_muscle", "")).strip() or "UNKNOWN"
        muscle_counts[primary] += 1
    print(f"  Day {day_n} ({name}): {count} exercises — muscles distribution = {dict(muscle_counts)}")
    if count < 5:
        print("    ❌ FAIL: count below Intermediate floor=5")
        ok = False
    elif count < 7:
        print("    ⚠️  pass but below 7-lift expectation for 90-min day")
    else:
        print("    ✅ OK")
print()
print("PLAN GENERATION OUTCOME:", "ALL DAYS GREEN >=5 floor — fixes worked" if ok else "FAIL — need investigate")
