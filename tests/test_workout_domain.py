import unittest

from domain.dashboard_metrics import get_weekly_progress
from domain.exercise_substitution import get_exercise_substitutions
from domain.exercise_rules import get_exercise_instruction, get_exercise_coaching
from domain.performance import get_progression_target
from domain.program_presets import PROGRAM_PRESETS, get_program_preset
from domain.workout_validation import has_duplicate_exercises
from presentation.session_state import initialize_session_state


class WorkoutDomainTests(unittest.TestCase):
    def test_duplicate_exercises_are_detected_across_days(self):
        plan = [
            {"exercises": [{"name": "Push-Up"}]},
            {"exercises": [{"name": "push-up"}]},
        ]
        self.assertTrue(has_duplicate_exercises(plan))

    def test_progression_increases_reps_until_cap(self):
        self.assertEqual(
            get_progression_target(
                {"weight_kg": 20, "actual_reps": 14},
                10,
            ),
            (20.0, 15),
        )

    def test_progression_handles_invalid_history(self):
        self.assertEqual(get_progression_target(None, "invalid"), (0.0, 8))

    def test_substitutions_respect_equipment_and_avoidance(self):
        alternatives = get_exercise_substitutions(
            {"name": "Bench Press", "primary_muscle": "Chest"},
            {"equipment": ["Dumbbells"], "exercises_to_avoid": "push-up"},
        )
        self.assertTrue(alternatives)
        self.assertNotIn("Push-Up", [item["name"] for item in alternatives])
        self.assertTrue(
            all(item["equipment"] in {"Bodyweight", "Dumbbells"} for item in alternatives)
        )

    def test_unknown_preset_is_custom(self):
        self.assertEqual(get_program_preset("missing"), PROGRAM_PRESETS["Custom"])

    def test_weekly_progress_has_eight_buckets(self):
        progress = get_weekly_progress([])
        self.assertEqual(len(progress), 8)
        self.assertTrue(all(item["Workouts"] == 0 for item in progress))

    def test_missing_instructions_get_safe_movement_guidance(self):
        guidance = get_exercise_instruction(
            {"name": "Squat", "movement_pattern": "Squat"}
        )
        self.assertIn("chest tall", guidance)

    def test_exercise_coaching_contains_beginner_cues(self):
        coaching = get_exercise_coaching(
            {"movement_pattern": "Horizontal Pull"}
        )
        self.assertEqual(len(coaching["steps"]), 3)
        self.assertTrue(coaching["breathing"])
        self.assertTrue(coaching["modification"])

    def test_session_initialization_preserves_auth_session(self):
        state = {"supabase_session": {"access_token": "existing"}}
        initialize_session_state(state)
        self.assertEqual(
            state["supabase_session"]["access_token"],
            "existing",
        )



if __name__ == "__main__":
    unittest.main()
