import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simulate: no GEMINI_API_KEY available so it uses fallback bucket logic.
os.environ.pop("GEMINI_API_KEY", None)

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
    "workout_duration": 90,
    "workout_duration_minutes": 90,
    "workout_location": "Gym",
    "physical_injuries": "NO",
    "workout_intensity": "Challenging",
}

# Stubs for streamlit imports (workout_generator calls st.secrets / st.error).
class _StubSecrets(dict):
    def get(self, key, default=None):
        return super().get(key, default)

class _StubSt:
    secrets = _StubSecrets()
    @staticmethod
    def error(msg):
        sys.stderr.write(f"[st.error fallback] {msg}\n")

import types
stub = types.ModuleType("streamlit")
stub.secrets = _StubSt.secrets
stub.error = _StubSt.error
stub.cache_resource = lambda **kw: (lambda fn: fn)
sys.modules["streamlit"] = stub

from modules import workout_generator

print("== Fallback generation for Intermediate 5d/90min Hypertrophy ==")
plan = workout_generator.generate_weekly_plan(profile_user)
assert isinstance(plan, list), f"plan should be list, got {type(plan)}"
print(f"  days generated = {len(plan)}")
all_green = True
total = 0
for day in plan:
    n = len(day.get("exercises", []))
    total += n
    status = "✅ OK (>=5, expected 8)" if n >= 5 else "❌ FAIL <5"
    if n < 5:
        all_green = False
    print(f"  Day {day['day']} ({day.get('name','?')}): {n} exercises — {status}")
print(f"\nTotal exercises/week = {total} (expected ~40)")
print("\nFINAL OUTCOME: ", "ALL GREEN >=5 per day (fixed!)" if all_green else "FAILED — need further fixes")
sys.exit(0 if all_green else 1)
