import json
import logging
import time
import streamlit as st
from google import genai
from google.genai import types
import os

from domain.workout_validation import has_duplicate_exercises
from domain.workout_generation import get_exercise_count
from domain.warmup_cooldown import attach_to_weekly_plan

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

    # Profile-driven exercises per day.  This is the same count driver
    # used by the pure-domain plan generator so both code paths agree.
    count_per_day = int(
        get_exercise_count(
            _profile.get("workout_duration", duration),
            _profile,
        )
    )

    # ------------------------------------------------------------------
    # Local helper: same fallback builder used for both (a) no API key
    # available AND (b) any exception during the Gemini JSON path.  It
    # builds 9-deep exercise pools per split bucket and then slices the
    # first ``count_per_day`` so output always honors the profile-driven
    # count (e.g. Intermediate 90-min Hypertrophy = 8/day, not 3).
    # ------------------------------------------------------------------
    def _build_fallback_plan():
        def exercise(name, eq, pm, mp, ins, reps="12"):
            return {
                "name": name, "equipment": eq, "sets": 3, "reps": reps,
                "rest": "60s", "primary_muscle": pm,
                "movement_pattern": mp, "instructions": ins
            }

        fallback_exercises = {
            "push": [
                exercise("Hanuman Dand", "Bodyweight", "Chest & Shoulders", "Compound Push", "Flow from downward dog into a deep sweeping push-up."),
                exercise("Dumbbell Floor Press", "Dumbbells", "Chest", "Horizontal Push", "Press dumbbells upward while keeping shoulders packed."),
                exercise("Pike Push-Up", "Bodyweight", "Shoulders", "Vertical Push", "Lower crown of head between hands with controlled tempo."),
                exercise("Dumbbell Incline Press", "Dumbbells", "Upper Chest", "Horizontal Push", "30° incline bench, emphasize stretch at the bottom."),
                exercise("Close-Grip Bench Press (or Dumbbell)", "Dumbbells / Barbell", "Chest & Triceps", "Horizontal Push", "Hands inside shoulder width, elbows tucked 45°."),
                exercise("Cable Chest Fly", "Cable", "Chest", "Fly", "Controlled squeeze at the top, no heavy swinging."),
                exercise("Hindu Push-Up (Sadha Dand)", "Bodyweight", "Chest & Shoulders", "Compound Push", "Flow from downward dog through a long sweeping press-up."),
                exercise("Overhead Dumbbell Press", "Dumbbells", "Shoulders", "Vertical Push", "Neutral spine, press straight up without rib flare."),
                exercise("Chest Dips (or bench dip)", "Bodyweight / Parallel Bars", "Chest & Triceps", "Compound Push", "Lean forward slightly to bias chest."),
            ],
            "push_variant": [
                exercise("Ram Murti Dand", "Bodyweight", "Chest & Triceps", "Compound Push", "Slow isometric pause at the bottom of each flowing push-up."),
                exercise("Single-Arm Dumbbell Press", "Dumbbells", "Chest", "Unilateral Push", "Press one dumbbell from the floor while bracing the opposite side."),
                exercise("Close-Grip Push-Up", "Bodyweight", "Triceps", "Horizontal Push", "Keep elbows close to ribs throughout each repetition."),
                exercise("Barbell / Dumbbell Spoto Press", "Dumbbells / Barbell", "Chest", "Horizontal Push", "Pause 1 inch above chest, strict form, no bounce."),
                exercise("Decline Dumbbell Press", "Dumbbells", "Lower Chest", "Horizontal Push", "15° decline bench, tension kept on lower sternal fibers."),
                exercise("Dumbbell Lateral Raise", "Dumbbells", "Side Delts", "Shoulder Abduction", "Slow raise to ear height, no leg drive, no swinging."),
                exercise("Z Press (seated overhead press)", "Dumbbells / Barbell", "Shoulders & Triceps", "Vertical Push", "Seated on floor, legs straight, strict no-leg-drive press."),
                exercise("Cable Triceps Push-Down", "Cable", "Triceps", "Elbow Extension", "Keep elbows pinned to sides, full lockout at bottom."),
                exercise("Bodyweight Diamond Push-Up", "Bodyweight", "Triceps & Inner Chest", "Horizontal Push", "Hands form a diamond under sternum, full range of motion."),
            ],
            "pull": [
                exercise("Inverted Row", "Bodyweight", "Back", "Horizontal Pull", "Pull chest toward a secure bar or table edge while keeping body straight."),
                exercise("Dumbbell Bent-Over Row", "Dumbbells", "Back", "Horizontal Pull", "Row toward hips with a neutral spine."),
                exercise("Band Face Pull", "Resistance Band", "Rear Delts", "Horizontal Pull", "Pull band toward the face and rotate hands outward."),
                exercise("Pull-Up (or Lat Pulldown)", "Pull-up Bar / Cable", "Lats", "Vertical Pull", "Chest to the bar, control the eccentric fully."),
                exercise("Chin-Up (or assisted)", "Pull-up Bar", "Lats & Biceps", "Vertical Pull", "Supinated grip, pull chest high, no kipping."),
                exercise("Dumbbell Single-Arm Row", "Dumbbells", "Mid-Back", "Unilateral Pull", "One hand on bench, pull dumbbell toward hip, squeeze scapula."),
                exercise("Towel Pull-Up / Lat Pulldown", "Towel / Cable", "Forearms & Lats", "Vertical Pull", "Grip towel ends, adds grip and forearm stimulus."),
                exercise("Seated Cable Row", "Cable", "Mid-Back", "Horizontal Pull", "Chest up, pull handle to lower sternum, squeeze shoulder blades."),
                exercise("Dumbbell Reverse Fly", "Dumbbells", "Rear Delts", "Horizontal Pull", "Bent over 45°, open arms wide, no momentum."),
            ],
            "pull_variant": [
                exercise("Towel Door Row", "Towel", "Upper Back", "Horizontal Pull", "Brace the feet and row against a securely anchored towel."),
                exercise("Renegade Row", "Dumbbells", "Back & Core", "Unilateral Pull", "Alternate rows from a stable plank position."),
                exercise("Dumbbell Pullover", "Dumbbell", "Lats", "Shoulder Extension", "Lower one dumbbell behind the head and pull it back over the chest."),
                exercise("Meadows Row (single-arm landmine)", "Dumbbells / Barbell", "Lats", "Horizontal Pull", "One end of bar anchored, row with wide grip on opposite end."),
                exercise("Wide-Grip Cable Lat Pulldown", "Cable", "Lats", "Vertical Pull", "Pull to upper chest, pause, slow eccentric."),
                exercise("Dumbbell Shrug", "Dumbbells", "Trapezius", "Scapular Elevation", "Shrug straight up, hold 1s, lower slow."),
                exercise("Cable Straight-Arm Pulldown", "Cable", "Lats", "Shoulder Extension", "Straight arms, press bar down to thighs, strict form."),
                exercise("Hammer Curl", "Dumbbells", "Biceps & Forearms", "Elbow Flexion", "Neutral (hammer) grip, curl without swinging."),
                exercise("Barbell Bent-Over Yates Row", "Barbell / Dumbbells", "Upper Back", "Horizontal Pull", "Slightly upright torso, row to hip crease, explosively controlled."),
            ],
            "legs": [
                exercise("Bethak", "Bodyweight", "Quadriceps", "Squat", "Perform a deep traditional squat with an upright torso."),
                exercise("Dumbbell Romanian Deadlift", "Dumbbells", "Hamstrings", "Hip Hinge", "Hinge at the hips while keeping dumbbells close to the legs."),
                exercise("Reverse Lunge", "Bodyweight", "Glutes & Legs", "Unilateral Squat", "Step back softly and drive through the front foot."),
                exercise("Back Squat (or Goblet Squat)", "Dumbbells / Barbell", "Quadriceps & Glutes", "Squat", "Squat below parallel, knees tracking over toes."),
                exercise("Walking Lunge", "Dumbbells / Bodyweight", "Legs & Glutes", "Unilateral Squat", "Alternate lunges forward, torso upright, front knee > 90°."),
                exercise("Hip Thrust (or Glute Bridge, weighted)", "Barbell / Dumbbells", "Glutes", "Hip Extension", "Upper back on bench, drive hips up, squeeze glutes 1s top."),
                exercise("Bulgarian Split Squat", "Dumbbells / Bodyweight", "Quads & Glutes", "Unilateral Squat", "Rear foot elevated, front knee tracking over toe."),
                exercise("Sumo Deadlift", "Dumbbells / Barbell", "Hamstrings, Glutes, Full Posterior", "Hip Hinge", "Wide stance, flat back, drive through heels."),
                exercise("Barbell / Dumbbell Front Squat", "Barbell / Dumbbells", "Quadriceps", "Squat", "Rack dumbbells on shoulders, elbows high, upright torso."),
            ],
            "legs_variant": [
                exercise("Hanuman Bethak", "Bodyweight", "Legs", "Dynamic Squat", "Alternate a deep squat with a controlled forward-reaching step."),
                exercise("Goblet Squat", "Dumbbell", "Quadriceps", "Squat", "Hold weight at the chest and squat below parallel as mobility allows."),
                exercise("Single-Leg Glute Bridge", "Bodyweight", "Glutes", "Hip Extension", "Drive the hips upward while keeping the pelvis level."),
                exercise("Barbell / Dumbbell Walking Lunge", "Dumbbells / Barbell", "Legs", "Unilateral Squat", "Step long, torso upright, drop back knee gently."),
                exercise("Roman Chair / Bench Back Extension", "Bodyweight / Dumbbells", "Lower Back & Glutes", "Hip Extension", "Hold plate at chest, hinge, squeeze glutes at the top."),
                exercise("Standing Calf Raise", "Bodyweight / Dumbbells", "Calves", "Plantar Flexion", "Full range: bottom stretch + top squeeze, 2s holds."),
                exercise("Dumbbell Step-Up", "Dumbbells / Bodyweight", "Quadriceps & Glutes", "Unilateral Step", "Drive through heel of lead leg, no push-off from back."),
                exercise("Kettlebell / Dumbbell Swing", "Dumbbells / Kettlebell", "Glutes & Hamstrings", "Hip Hinge", "Hinge at hips, swing dumbbell to eye level with core braced."),
                exercise("Seated Leg Curl (machine) / Nordic Curl (bodyweight)", "Machine / Bodyweight", "Hamstrings", "Knee Flexion", "Slow eccentric, control descent fully."),
            ],
            "legs_variant_2": [
                exercise("Cossack Squat", "Bodyweight", "Adductors & Glutes", "Lateral Squat", "Shift into one hip while extending the opposite leg to the side."),
                exercise("Dumbbell Step-Up", "Dumbbell", "Quadriceps & Glutes", "Unilateral Step", "Step onto a stable platform and stand tall through the leading leg."),
                exercise("Standing Calf Raise", "Bodyweight", "Calves", "Plantar Flexion", "Rise onto balls of feet and lower slowly."),
                exercise("Lateral Band Walks", "Resistance Band", "Glute Medius", "Hip Abduction", "Band above knees, side-step, keep knees pushed out."),
                exercise("Barbell Hip Thrust", "Barbell / Dumbbells", "Glutes", "Hip Extension", "Upper back on bench, drive hips high, pause 2s top."),
                exercise("Single-Leg Romanian Deadlift", "Dumbbells / Bodyweight", "Hamstrings & Glutes", "Unilateral Hip Hinge", "Hip-hinge back, keep back flat, reach arms forward."),
                exercise("Dumbbell Forward Lunge + Twist", "Dumbbells / Bodyweight", "Legs & Core", "Rotational Lunge", "Lunge forward, rotate torso over lead leg."),
                exercise("Jump Squat (or bodyweight)", "Bodyweight / Dumbbells", "Quads & Glutes", "Explosive Squat", "Squat to parallel, jump, land soft with control."),
                exercise("Tibialis Raise (bodyweight / plate)", "Bodyweight / Plate", "Shins / Tibialis Anterior", "Dorsiflexion", "Toes elevated, shift weight back onto heels to target shin."),
            ],
            "shoulders_core": [
                exercise("Dumbbell Arnold Press", "Dumbbells", "Shoulders", "Vertical Push", "Rotate palms as weights travel from chest height to overhead."),
                exercise("Lateral Raise", "Dumbbells", "Side Delts", "Shoulder Abduction", "Raise weights to shoulder height without shrugging."),
                exercise("Dead Bug", "Bodyweight", "Core", "Anti-Extension", "Brace the abdomen while slowly extending opposite limbs."),
                exercise("Dumbbell Front Raise", "Dumbbells", "Anterior Delts", "Shoulder Flexion", "Raise straight in front to shoulder height, slow eccentric."),
                exercise("Reverse Fly", "Dumbbells", "Rear Delts", "Horizontal Pull", "Hinge at hips, open arms wide, squeeze shoulder blades."),
                exercise("Plank Shoulder Taps", "Bodyweight", "Shoulders & Core", "Anti-Rotation", "High plank, tap opposite shoulder, no hip sag or twist."),
                exercise("Hanging Leg Raise / Bent Knee Raise", "Pull-up Bar / Bench", "Lower Abs", "Hip Flexion", "Controlled raise, no swing, return slow."),
                exercise("Face Pull (cable)", "Cable", "Rear & Side Delts", "Horizontal Pull", "Pull rope toward forehead, externally rotate at top."),
                exercise("Hollow Body Hold", "Bodyweight", "Core", "Anti-Extension", "Lower back pressed to floor, hold hollow position 20-30s."),
            ],
            "shoulders": [
                exercise("Dumbbell Push Press", "Dumbbells", "Shoulders", "Explosive Push", "Use a shallow leg drive to press the weights overhead."),
                exercise("Bent-Over Reverse Fly", "Dumbbells", "Rear Delts", "Horizontal Pull", "Open the arms wide with a stable, flat back."),
                exercise("Bear Plank Shoulder Tap", "Bodyweight", "Shoulders & Core", "Anti-Rotation", "Tap opposite shoulders from a low bear-plank position."),
                exercise("Seated Overhead Press", "Dumbbells / Barbell", "Shoulders & Triceps", "Vertical Push", "Back supported, press strict overhead, no rib flare."),
                exercise("Dumbbell Y Raise", "Dumbbells", "Rear Delts", "Shoulder Scaption", "Hinge 45°, raise dumbbells into Y-shape overhead."),
                exercise("Upright Row", "Dumbbells / Cable", "Side Delts & Traps", "Upright Pull", "Pull bar to collar bones, elbows above wrists."),
                exercise("Kettlebell / Dumbbell Single-Arm Overhead Press", "Dumbbells", "Shoulders", "Unilateral Vertical Push", "Single dumbbell, press overhead, anti-rotation bracing."),
                exercise("Band Pull-Apart", "Resistance Band", "Rear Delts", "Horizontal Pull", "Pull band apart at chest height, squeeze rear delts."),
                exercise("Dumbbell Lateral Walk (overhead)", "Dumbbells", "Shoulders & Core", "Carry", "Light dumbbells locked overhead, walk 10-20 steps per set."),
            ],
            "arms_core": [
                exercise("Alternating Dumbbell Curl", "Dumbbells", "Biceps", "Elbow Flexion", "Curl one weight at a time without swinging."),
                exercise("Overhead Triceps Extension", "Dumbbell", "Triceps", "Elbow Extension", "Lower the weight behind head while keeping elbows pointed forward."),
                exercise("Mountain Climber", "Bodyweight", "Core", "Dynamic Conditioning", "Drive alternating knees toward the chest from a strong plank."),
                exercise("Dumbbell Hammer Curl", "Dumbbells", "Biceps & Forearms", "Elbow Flexion", "Neutral grip, curl, no body swing."),
                exercise("Cable Triceps Push-Down (V-bar)", "Cable", "Triceps", "Elbow Extension", "Tight to ribs, full lockout at bottom."),
                exercise("Barbell / Dumbbell Preacher Curl", "Dumbbells / Barbell", "Biceps", "Elbow Flexion", "Pad under elbows, strict curl, squeeze at top."),
                exercise("Weighted Crunch (or plate)", "Plate / Dumbbells", "Upper Abs", "Spinal Flexion", "Hold plate at chest, sit up, controlled descent."),
                exercise("Dumbbell Farmer's Carry", "Dumbbells", "Forearms, Core, Traps", "Loaded Carry", "Heavy dumbbells at sides, walk tall, braced core."),
                exercise("Russian Twist (weighted)", "Plate / Dumbbells", "Obliques & Core", "Spinal Rotation", "Lean back ~45°, tap floor side-to-side."),
            ],
            "full_body": [
                exercise("Wrestler Sapate", "Bodyweight", "Full Body", "Explosive Conditioning", "Flow through a squat, dand, and jump."),
                exercise("Dumbbell Thruster", "Dumbbells", "Full Body", "Squat to Push", "Stand from a front squat and finish with a controlled press."),
                exercise("Bear Crawl", "Bodyweight", "Full Body", "Locomotion", "Move forward slowly while keeping knees close to the floor."),
                exercise("Dumbbell Clean & Press", "Dumbbells", "Full Body", "Olympic Lift", "Clean dumbbells to shoulders, then press overhead."),
                exercise("Burpee (traditional or sapate)", "Bodyweight", "Full Body", "Explosive Conditioning", "Squat → plank → push-up → jump."),
                exercise("Kettlebell or Dumbbell Snatch", "Dumbbells", "Full Body", "Olympic Lift", "Hinge, pull, punch dumbbell overhead, lock out."),
                exercise("Squat + Push-Up Complex (ladder)", "Bodyweight", "Full Body", "Mixed", "1 squat + 1 push-up → 2+2 → up to 5+5."),
                exercise("Dumbbell Romanian Deadlift + Row Combo", "Dumbbells", "Posterior Chain + Back", "Hinge + Pull", "RDL bottom, hold, then row both dumbbells to hips."),
                exercise("Surya Namaskar B (3-5 rounds)", "Bodyweight", "Full Body", "Mobility + Conditioning", "Flow: Upward Dog → Downward Dog → Jump Forward → Chair Pose."),
            ],
            "full_body_variant": [
                exercise("Hindu Push-Up to Squat", "Bodyweight", "Full Body", "Compound Conditioning", "Flow from a push-up into a deep squat without losing control."),
                exercise("Dumbbell Clean", "Dumbbells", "Full Body", "Olympic Pull", "Drive through hips to bring dumbbells to the shoulders."),
                exercise("Walking Lunge with Twist", "Bodyweight", "Full Body", "Rotational Lunge", "Step forward and rotate gently over the lead leg."),
                exercise("Dumbbell Man Maker", "Dumbbells", "Full Body", "Compound Conditioning", "Plank row → push-up → squat clean → shoulder press."),
                exercise("Turkish Get-Up (half, light)", "Dumbbell / Kettlebell", "Full Body", "Complex Strength", "Light weight, master form, full shoulder stability."),
                exercise("Gada / Clubbell 360 Swings (else dumbbell halo)", "Mudgar / Dumbbells", "Core & Shoulders", "Rotational Core", "Rotate dumbbell around head, keep core tight."),
                exercise("Alternating Dumbbell Snatch", "Dumbbells", "Full Body", "Olympic Lift", "Alternating single-arm snatches, explosive hip drive."),
                exercise("Battle Rope Slams (or towel whip)", "Rope / Towel", "Full Body", "Conditioning", "Heavy whipping motion, explosive hips + arms."),
                exercise("Goblet Squat + Press (complex)", "Dumbbell / Kettlebell", "Full Body", "Squat + Push", "Goblet squat → stand → press weight overhead."),
            ],
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

            pool = fallback_exercises.get(exercise_key, fallback_exercises["full_body"])
            how_many = max(3, min(count_per_day, len(pool)))
            chosen_exercises = pool[:how_many]
            weekly_plan.append({
                "day": i, "name": f"Hybrid {d_name} Split",
                "duration": duration, "intensity": intensity,
                "warmup": "5 mins", "cooldown": "5 mins",
                "exercises": chosen_exercises,
            })
        return weekly_plan

    # No API key → use structural fallback directly.  Do not return [].
    if not api_key:
        return attach_to_weekly_plan(_build_fallback_plan())

    client = _get_gemini_client(api_key)

    prompt = f"""
    You are an elite master strength coach specializing in Hybrid Functional Training. Your unique expertise seamlessly blends modern Western hypertrophy/strength concepts with traditional Indian physical culture (Vyayam training patterns from ancient Akhadas).
    
    Days per week: {days_per_week} days
    Program Preset: {program_preset}
    Workout Style: {workout_style} (Hybrid Western & Indian Traditional)
    Fitness Goal: {fitness_goal}
    Fitness Level: {fitness_level}
    Target Session Duration: {duration} minutes per day
    Target Exercises Per Day: EXACTLY {count_per_day} exercises per split day (MIN floor for stated level: {4 if str(fitness_level).lower() == 'beginner' else 5})
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

    MANDATORY EXERCISE COUNT RULE (ENFORCED, NON-NEGOTIABLE):
    - EVERY split day MUST have EXACTLY {count_per_day} exercises in its ``exercises`` array.
    - DO NOT return 3, 4 or 5 exercises.  Target count is {count_per_day}.  This count was derived from duration × fitness_level × weekly_frequency × workout_style drivers.
    - For Chest & Triceps / Back & Biceps / Upper / Lower / Legs / Push / Pull days: LARGER compound groups (chest, back, quads) should occupy 50-65% of the {count_per_day} slots, smaller muscles (triceps, biceps, core, shoulders) fill the rest, to avoid "all triceps" style imbalance.
    - For Full Body days: every compound major muscle group must appear at least once.
    
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
                # 5 days × 8 exercises × 9 keys per exercise = ~40-50 KB JSON.
                # 3000 tokens was too small → Gemini truncated at ~3 exercises/day
                # to fit budget.  9000 tokens = ~36 KB which is safely above the
                # expected payload size for a 7-day × 9-exercise week.
                max_output_tokens=9000,
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
        return attach_to_weekly_plan(generated_plan)
    except Exception as e:
        st.error(f"AI GENERATION ENGINE CRASHED: {str(e)}")
        return attach_to_weekly_plan(_build_fallback_plan())


@st.cache_resource(show_spinner=False)
def _get_gemini_client(api_key):
    """Reuse the Gemini client across Streamlit reruns."""
    return genai.Client(api_key=api_key)
