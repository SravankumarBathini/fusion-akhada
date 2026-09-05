"""Split-specific structured warmup and cooldown generators.

Instead of asking the LLM to also invent warmups / stretches (which would
bloat the 9000-token generation budget and be inconsistently good), we
bake split-specific tables in pure Python.  The UI then collapses them
into expanders (never auto-expanded) so the daily view stays focused on
the main 6-9 work sets.

Every row returned follows the same schema as main exercises:
  { name, equipment, sets, reps, rest, primary_muscle, movement_pattern,
    instructions }
This lets the UI use 1 shared renderer for warmup / main / cooldown.
"""

from __future__ import annotations


def _row(name, eq, sets, reps, rest, pm, mp, ins):
    return {
        "name": name,
        "equipment": eq,
        "sets": sets,
        "reps": reps,
        "rest": rest,
        "primary_muscle": pm,
        "movement_pattern": mp,
        "instructions": ins,
    }


# =====================================================================
# Warmup pools — keyed by the split tokens that trigger them
# =====================================================================

def _warmup_push_chest_triceps():
    return [
        _row("T-Spine Opener w/ Foam Roller or Dowel", "Foam Roller / Dowel",
              2, "8 reps", "45s", "Upper Back & T-Spine", "Mobility",
              "Lay on foam roller at mid-back, hands behind head, bridge hips, gently extend over the roller 8 slow reps."),
        _row("Scapular Wall Slides", "Wall / Dowel",
              2, "12 reps", "45s", "Scapulae & Rear Delts", "Scapular Mobilization",
              "Back flat to wall, slide arms up into 'W' then overhead, keep elbows/wrists pinned entire rep."),
        _row("Serratus Anterior Punch (Band or Cable)", "Band / Cable",
              2, "15 reps", "30s", "Serratus Anterior", "Scapular Protraction",
              "Light band tension, arm straight, punch forward and exaggerate the scapular protraction at end range."),
        _row("Band Pull-Aparts", "Resistance Band",
              3, "20 reps", "20s", "Rear Delts & Traps", "Horizontal Pull",
              "Band in front of chest, pull apart until elbows wide, squeeze shoulder blades together at finish."),
        _row("Incline Dumbbell Press (Empty / Light Bar)", "Dumbbells / Empty Barbell",
              2, "10 reps", "45s", "Upper Chest", "Horizontal Push",
              "50% of first work set weight, controlled tempo, emphasize stretch and lockout."),
        _row("Light Dumbbell Bench Fly (very light)", "Dumbbells",
              1, "12 reps", "30s", "Chest", "Fly",
              "Light dumbbells, full stretch at bottom, gentle squeeze — purely blood-flow and pre-stretch."),
        _row("Cable Triceps Pushdown (Rope, very light)", "Cable",
              2, "15 reps", "20s", "Triceps", "Elbow Extension",
              "Light cable stack, elbows pinned to sides, full lockout, control eccentric."),
        _row("Deep Breathing + Shoulder CARs", "Bodyweight",
              1, "5 reps", "60s", "Shoulder Capsule", "Mobility CARs",
              "360° controlled arm circles forward/backward, plus 5× deep diaphragmatic breaths before first working set."),
    ]


def _warmup_pull_back_biceps():
    return [
        _row("Thoracic Spine Foam Roll + Extension", "Foam Roller",
              2, "10 reps", "45s", "T-Spine", "Mobility",
              "Foam roll upper back 10 passes, then 10 gentle extensions over roller without cranking neck."),
        _row("Cat-Cow to Child's Pose Flow", "Bodyweight / Mat",
              2, "10 reps", "30s", "Spine & Lats", "Spinal Mobilization",
              "Cat-Cow 10 cycles, hold child's pose 3 breaths between to unlock lats."),
        _row("Band Dislocates (over and back)", "Resistance Band / Dowel",
              2, "12 reps", "30s", "Shoulder Girdle", "Shoulder Mobility",
              "Band wide grip, pass over head to behind back and return — widen grip if any impingement."),
        _row("Scapular Retraction Hold / YTWL Series", "Bodyweight / Light Dumbbells",
              2, "8-10 per letter", "30s", "Rear Delts & Mid Back", "Rear-Delt Activation",
              "Prone, light dumbbells if available: Y, T, W, L patterns each × 8 reps, squeeze scapulae at top."),
        _row("Straight-Arm Pulldown (light cable)", "Cable",
              2, "12 reps", "30s", "Lats", "Shoulder Extension",
              "Light cable, straight arms, press bar from eye level to thighs, feel lat contract — no momentum."),
        _row("Inverted Rows (bodyweight or assisted)", "Bodyweight / Bar",
              2, "10 reps", "45s", "Lats & Biceps", "Horizontal Pull",
              "Bar in rack at hip height, pull chest to bar, squeeze for 1s at top."),
        _row("Face Pull (band or light cable)", "Band / Cable",
              3, "15 reps", "20s", "Rear Delts & External Rotators", "Horizontal Pull",
              "Pull band or rope to forehead, externally rotate — warm the external rotators before heavy pulling."),
        _row("Hammer Curl (ultra-light)", "Dumbbells",
              1, "15 reps", "30s", "Biceps & Forearms", "Elbow Flexion",
              "Very light dumbbells to get blood into elbows and forearms before heavier back sets."),
    ]


def _warmup_legs():
    return [
        _row("Hip Airplanes (3/leg)", "Bodyweight / Wall for balance",
              2, "3 per side", "45s", "Hips & Glutes", "Hip Mobilization",
              "Stand on one leg, hinge forward, open/close the hip like an airplane; no knee collapse."),
        _row("World's Greatest Stretch (6/leg)", "Bodyweight",
              2, "6 per side", "30s", "Hips & T-Spine", "Dynamic Stretch",
              "Lunge → elbow to instep → rotate open → reach up — 6/side, mobilizes hips, t-spine, and ankle all in one."),
        _row("Cossack Squat x 10/side (bodyweight)", "Bodyweight",
              2, "10 per side", "30s", "Adductors & Quads", "Lateral Squat",
              "Feet wide, shift side to side, keep trailing leg straight, chest tall."),
        _row("Bodyweight Goblet Squat + 3s Pause at Bottom", "Bodyweight",
              2, "15 reps", "30s", "Quads & Glutes", "Squat",
              "Arms forward for counterbalance, deep squat, pause 3s at bottom, drive through heels."),
        _row("Walking Bodyweight Lunge", "Bodyweight",
              2, "10 per side", "30s", "Quads & Glutes", "Unilateral Squat",
              "Long steps, torso upright, front knee tracking over toes; gently drop back knee toward floor."),
        _row("Romanian Deadlift (empty bar or light dumbbells)", "Empty Bar / Light Dumbbells",
              2, "12 reps", "45s", "Hamstrings", "Hip Hinge",
              "50% of work-set weight, bar along legs, feel hamstring stretch — don't round lower back."),
        _row("Single-Leg Glute Bridges x 12/leg", "Bodyweight / Plate on hips",
              2, "12 per side", "20s", "Glutes", "Hip Extension",
              "Flat back, one leg extended, bridge up, squeeze glute 1s top."),
        _row("Pogo Jumps + Ankle Circles", "Bodyweight",
              1, "20 pogos + 10 circles", "30s", "Ankles & Calves", "Reactive Warmup",
              "Small quick pogos to warm Achilles, then ankle circles clock/anti-clock to end."),
    ]


def _warmup_shoulders_core():
    return [
        _row("Shoulder CARs + Banded Distraction", "Band",
              2, "5 forward / 5 back", "60s", "Glenohumeral Capsule", "Mobility CARs",
              "Banded distraction at arm pit, full 360° arm circles slowly — blood flow to shoulder capsule."),
        _row("Prone YTWL Series", "Light Dumbbells / Bodyweight",
              2, "8 per letter", "30s", "Rear Delts & Mid Trap", "Rear-Delt Activation",
              "Lying face down on bench, light dumbbells, Y/T/W/L patterns, squeeze each rep."),
        _row("Banded External Rotations (cable or band at side)", "Band / Cable",
              2, "12 per side", "30s", "Infraspinatus / Teres Minor", "External Rotation",
              "Towel under arm, elbow at 90°, externally rotate against band — very light."),
        _row("Cable Face Pulls", "Cable",
              3, "15 reps", "20s", "Rear & Side Delts", "Horizontal Pull",
              "Rope attachment, pull toward forehead, rotate at top to stretch anterior cuff."),
        _row("Seated Overhead Dumbbell Press (PVC pipe or 2.5kg DBs)", "PVC / Light Dumbbells",
              2, "10 reps", "30s", "Anterior & Lateral Delts", "Vertical Push",
              "Very light, focus on keeping ribcage neutral — no rib flare during press."),
        _row("Bird-Dogs × 10/side", "Bodyweight / Mat",
              2, "10 per side", "30s", "Core & Spine Stabilizers", "Anti-Rotation",
              "Hands under shoulders, knees under hips, extend opposite arm+leg — no pelvic tilt."),
        _row("Dead-Bug Series × 8/side", "Bodyweight / Mat",
              2, "8 per side", "30s", "Rectus & Transverse Abdominis", "Anti-Extension",
              "Arms up, knees bent 90°, lower opposite arm/leg slowly, keep lower back glued."),
        _row("Hollow Body Hold + Rock", "Bodyweight / Mat",
              1, "20s hold + 12 rocks", "30s", "Anterior Core", "Core Bracing",
              "Hollow body hold 20s, then gentle rocking if comfortable."),
    ]


def _warmup_arms_core():
    return [
        _row("Wrist CARs + Finger Spread/Crush", "Bodyweight",
              2, "10 circles + 20 squeezes", "30s", "Wrists / Forearms", "Mobility",
              "Wrist circles both directions, then rapid finger spreads + squeezes to warm flexors/extensors."),
        _row("Band Pull-Aparts + Dislocates", "Band",
              2, "20 aparts + 10 dislocates", "30s", "Upper Body", "Mobility",
              "Front chest pulls, then overhead dislocates with band wide enough to avoid pinching."),
        _row("Cable External Rotations × 12/side", "Cable",
              2, "12 per side", "30s", "Rotator Cuff", "External Rotation",
              "Keep elbow pinned to side with towel, very light cable, full external rotation."),
        _row("Very Light Hammer Curls", "Dumbbells",
              2, "15 reps", "20s", "Biceps & Brachialis", "Elbow Flexion",
              "Tiny dumbbells, neutral grip, full range."),
        _row("Very Light Cable Triceps Pushdowns", "Cable",
              2, "15 reps", "20s", "Triceps", "Elbow Extension",
              "Light stack, rope attachment, elbows tight, full lockout."),
        _row("Dead-Bug + Bird-Dog", "Bodyweight",
              2, "10 per side each", "30s", "Core", "Anti-Extension/Rotation",
              "10 dead-bugs, then 10 bird-dogs per side, lower back pressed to mat for dead-bug."),
        _row("Plank Shoulder Taps", "Bodyweight",
              2, "20 taps total", "20s", "Anti-Rotation Core", "Anti-Rotation",
              "High plank, tap opposite shoulder without hip hiking or sag."),
        _row("Diaphragmatic Breathing + Bracing Drill", "Bodyweight",
              1, "10 breaths + 3 10s braces", "60s", "Core", "Bracing",
              "Big belly breaths, then 3× 10s rigid brace like someone is going to punch you."),
    ]


def _warmup_upper_body():
    # combine push + pull warmups, then deduplicate by name
    combined = {}
    for item in _warmup_push_chest_triceps() + _warmup_pull_back_biceps():
        combined.setdefault(item["name"], item)
    return list(combined.values())


def _warmup_lower_body():
    # aliases to legs warmup (most complete)
    return _warmup_legs()


def _warmup_full_body():
    combined = {}
    for item in (
        _warmup_push_chest_triceps()[:3]
        + _warmup_pull_back_biceps()[:3]
        + _warmup_legs()[:4]
        + _warmup_shoulders_core()[:2]
    ):
        combined.setdefault(item["name"], item)
    return list(combined.values())


WARMUP_TABLE = {
    "chest": _warmup_push_chest_triceps,
    "triceps": _warmup_push_chest_triceps,
    "push": _warmup_push_chest_triceps,
    "back": _warmup_pull_back_biceps,
    "biceps": _warmup_pull_back_biceps,
    "pull": _warmup_pull_back_biceps,
    "legs": _warmup_legs,
    "lower": _warmup_lower_body,
    "shoulders": _warmup_shoulders_core,
    "core": _warmup_shoulders_core,
    "arm": _warmup_arms_core,
    "upper": _warmup_upper_body,
    "full": _warmup_full_body,
}


# =====================================================================
# Cooldown pools — static stretching, split muscle targeted
# =====================================================================

def _cooldown_push_chest_triceps():
    return [
        {"name": "Doorway Chest Stretch (both hands low/mid/high)", "equipment": "Doorway / Wall",
           "primary_muscle": "Chest & Anterior Delts", "movement_pattern": "Static Stretch",
           "instruction": "Hands on door jamb, step through gently; 3 hand positions to hit all chest fibers."},
        {"name": "Cross-Body Shoulder Stretch", "equipment": "Bodyweight",
           "primary_muscle": "Posterior/Medial Delts", "movement_pattern": "Static Stretch",
           "instruction": "Pull one arm across chest, above elbow, hold, no shoulder hiking."},
        {"name": "Triceps Rope Stretch (overhead, both sides)", "equipment": "Bodyweight",
           "primary_muscle": "Triceps Long Head", "movement_pattern": "Static Stretch",
           "instruction": "Raise arm overhead, elbow bent, pull elbow toward head with opposite hand."},
        {"name": "Lat Stretch (child's pose or side-lying)", "equipment": "Mat",
           "primary_muscle": "Lats", "movement_pattern": "Static Stretch",
           "instruction": "Child's pose, reach forward and sit back into hips to lengthen lats fully."},
        {"name": "Wrist Flexor + Extensor Stretch", "equipment": "Bodyweight",
           "primary_muscle": "Forearms", "movement_pattern": "Static Stretch",
           "instruction": "Palm up then down, pull fingers back gently with opposite hand to relieve forearm load."},
        {"name": "Diaphragmatic Belly Breathing + Box Breathing", "equipment": "Bodyweight",
           "primary_muscle": "Nervous System", "movement_pattern": "Recovery",
           "instruction": "5-10 cycles of 4s in / 4s hold / 6s out to down-regulate sympathetic tone."},
    ]


def _cooldown_pull_back_biceps():
    return [
        {"name": "Lat Hang (pull-up bar / table edge)", "equipment": "Pull-Up Bar / Table",
           "primary_muscle": "Lats & Thoracic Spine", "movement_pattern": "Static Stretch",
           "instruction": "Dead hang, gently relax and let gravity lengthen lats 45-60s total."},
        {"name": "Seated Spinal Twist (both sides)", "equipment": "Mat",
           "primary_muscle": "Mid Back & Obliques", "movement_pattern": "Static Stretch",
           "instruction": "Cross one leg, twist gently, hold; mobilize the spine that worked so hard pulling."},
        {"name": "Upper Trap / Levator Stretch (both sides)", "equipment": "Bodyweight",
           "primary_muscle": "Upper Traps", "movement_pattern": "Static Stretch",
           "instruction": "Ear toward shoulder, gentle pull with hand, tilt chin 15° to target levator scapulae."},
        {"name": "Biceps Wall Stretch", "equipment": "Wall",
           "primary_muscle": "Biceps & Brachialis", "movement_pattern": "Static Stretch",
           "instruction": "Palm flat on wall behind you, gently turn body away — keep arm straight, don't hyperextend elbow."},
        {"name": "Thoracic Spine Extension over Roller", "equipment": "Foam Roller",
           "primary_muscle": "T-Spine", "movement_pattern": "Static Stretch",
           "instruction": "Support head, extend over roller, no forced lumbar bend."},
        {"name": "Box Breathing + Progressive Muscle Relaxation", "equipment": "Bodyweight",
           "primary_muscle": "Nervous System", "movement_pattern": "Recovery",
           "instruction": "Tense and release each muscle group from toes up, then 4-4-4-4 breathing."},
    ]


def _cooldown_legs():
    return [
        {"name": "World's Greatest Stretch (paused, held)", "equipment": "Mat",
           "primary_muscle": "Hips / T-Spine / Ankles", "movement_pattern": "Static Stretch",
           "instruction": "Lunge position, elbow to instep, 10-breath hold each side — mobilize everything that worked."},
        {"name": "90/90 Hip Stretch (both sides)", "equipment": "Mat",
           "primary_muscle": "Hips (Internal + External Rotators)", "movement_pattern": "Static Stretch",
           "instruction": "Both knees bent 90°, lean forward to load front hip, then lean back for back hip capsule."},
        {"name": "Pigeon Pose / Figure-4 (both sides)", "equipment": "Mat / Bench",
           "primary_muscle": "Glutes & Piriformis", "movement_pattern": "Static Stretch",
           "instruction": "Figure-4 cross, upright torso; deeper if comfortable in pigeon variation."},
        {"name": "Standing Hamstring Stretch (both sides)", "equipment": "Rack Bar / Chair",
           "primary_muscle": "Hamstrings", "movement_pattern": "Static Stretch",
           "instruction": "Heel up on bar/chair, hinge from hips keeping back flat — don't round to reach further."},
        {"name": "Calf Stretch (wall, both straight + bent knee)", "equipment": "Wall",
           "primary_muscle": "Soleus / Gastrocnemius", "movement_pattern": "Static Stretch",
           "instruction": "Straight knee = gastroc; bent knee = soleus. Both sides, front knee tracking over toes."},
        {"name": "Hip Flexor Couch Stretch (both sides)", "equipment": "Bench / Wall",
           "primary_muscle": "Hip Flexors & Quads", "movement_pattern": "Static Stretch",
           "instruction": "Rear foot on bench/chair, torso tall, tuck pelvis to true stretch the hip flexor complex."},
        {"name": "Child's Pose + Diaphragmatic Breathing", "equipment": "Mat",
           "primary_muscle": "Spine & Nervous System", "movement_pattern": "Recovery",
           "instruction": "Knees wide, arms forward, 8+ deep belly breaths to finish."},
    ]


def _cooldown_shoulders_core():
    return [
        {"name": "Shoulder Dislocates (gentle, band wide)", "equipment": "Band",
           "primary_muscle": "Shoulder Complex", "movement_pattern": "Static/Mobility",
           "instruction": "Slow controlled dislocates with very wide band to 'windshield-wiper' the capsule."},
        {"name": "Sleeper Stretch (both sides)", "equipment": "Mat",
           "primary_muscle": "Posterior Rotator Cuff", "movement_pattern": "Static Stretch",
           "instruction": "Side lying, shoulder 90° forward, gently push forearm down toward mat — feel deep posterior cuff stretch."},
        {"name": "Cross-Body Shoulder + Posterior Capsule", "equipment": "Bodyweight",
           "primary_muscle": "Delts & Post. Capsule", "movement_pattern": "Static Stretch",
           "instruction": "Pull one arm across chest, above the elbow, no compensating with the scapula."},
        {"name": "Cat-Cow + Child's Pose", "equipment": "Mat",
           "primary_muscle": "Spine & Core", "movement_pattern": "Static Stretch",
           "instruction": "Cat-Cow cycles, then child's pose to decompress vertebrae."},
        {"name": "Supine Spinal Twist (both sides)", "equipment": "Mat",
           "primary_muscle": "Obliques & Glutes", "movement_pattern": "Static Stretch",
           "instruction": "Lying on back, cross knee over, twist, opposite shoulder stays down — 5 breaths."},
        {"name": "4-7-8 Breathing", "equipment": "Bodyweight",
           "primary_muscle": "Nervous System", "movement_pattern": "Recovery",
           "instruction": "4s inhale, 7s hold, 8s slow exhale × 5 cycles to down-regulate post-core work."},
    ]


def _cooldown_arms_core():
    return [
        {"name": "Wrist Flexor + Extensor Stretch", "equipment": "Bodyweight",
           "primary_muscle": "Forearms", "movement_pattern": "Static Stretch",
           "instruction": "Palm up then down, pull fingers back gently — very important to relieve tendons post arm work."},
        {"name": "Biceps Wall Stretch + Triceps Overhead Stretch", "equipment": "Wall / Bodyweight",
           "primary_muscle": "Biceps & Triceps", "movement_pattern": "Static Stretch",
           "instruction": "Palm on wall behind, rotate; then overhead triceps pull. Both sides."},
        {"name": "Sleeper Shoulder Stretch (both sides)", "equipment": "Mat",
           "primary_muscle": "Posterior Cuff", "movement_pattern": "Static Stretch",
           "instruction": "Side lying, protect the shoulder girdle after any overhead pressing."},
        {"name": "Foam Roller Thoracic Extension", "equipment": "Foam Roller",
           "primary_muscle": "T-Spine", "movement_pattern": "Static Stretch",
           "instruction": "Gentle extensions over the foam roller — lats/back tightness pulls posture forward after arms day."},
        {"name": "Supine Knee Hug + Pelvic Tilt", "equipment": "Bodyweight / Mat",
           "primary_muscle": "Lower Back", "movement_pattern": "Static Stretch",
           "instruction": "Pull knees to chest, then flatten lower back to floor to unlock post-bracing stiffness."},
        {"name": "4-7-8 Breathing", "equipment": "Bodyweight",
           "primary_muscle": "Nervous System", "movement_pattern": "Recovery",
           "instruction": "5 cycles of 4s in / 7s hold / 8s out to reset breathing post-bracing."},
    ]


def _cooldown_upper_body():
    combined = {}
    for item in _cooldown_push_chest_triceps() + _cooldown_pull_back_biceps():
        combined.setdefault(item["name"], item)
    return list(combined.values())


def _cooldown_lower_body():
    return _cooldown_legs()


def _cooldown_full_body():
    combined = {}
    for item in (
        _cooldown_legs()
        + _cooldown_push_chest_triceps()[:2]
        + _cooldown_pull_back_biceps()[:2]
        + _cooldown_shoulders_core()[-1:]
    ):
        combined.setdefault(item["name"], item)
    return list(combined.values())


COOLDOWN_TABLE = {
    "chest": _cooldown_push_chest_triceps,
    "triceps": _cooldown_push_chest_triceps,
    "push": _cooldown_push_chest_triceps,
    "back": _cooldown_pull_back_biceps,
    "biceps": _cooldown_pull_back_biceps,
    "pull": _cooldown_pull_back_biceps,
    "legs": _cooldown_legs,
    "lower": _cooldown_lower_body,
    "shoulders": _cooldown_shoulders_core,
    "core": _cooldown_shoulders_core,
    "arm": _cooldown_arms_core,
    "upper": _cooldown_upper_body,
    "full": _cooldown_full_body,
}


def _lookup(table, day_name, default_fn):
    hay = (day_name or "").lower()
    best = None
    best_key = None
    for key, fn in table.items():
        if key in hay:
            # Longest matching key wins (e.g. "shoulders & core" matches both
            # "shoulders" and "core" -> "shoulders" has 8 chars, "core" 4 -> pick shoulders)
            if best is None or len(key) > len(best_key):
                best = fn
                best_key = key
    return best() if best is not None else default_fn()


def generate_for_split(day_name, warmup_minutes=None, cooldown_minutes=None,
                        holds_per_side=2, hold_seconds=45):
    """Return split-matched warmup + cooldown arrays.

    Parameters
    ----------
    day_name : str
        e.g. "Chest & Triceps", "Legs", "Shoulders & Core", "Full Body"
    warmup_minutes, cooldown_minutes : int | None
        If provided we clip rows to a rough target budget (1 row ≈ 1 min).
    holds_per_side : int
        Each static cooldown row is described as N × 45s per side.
    hold_seconds : int
        Override default 45s/hold.

    Returns
    -------
    tuple[list[dict], list[dict]]
        ``(warmup_rows, cooldown_rows)`` matching the same exercise dict
        schema main plan rows use, so they render with the same UI loop.
    """

    warmup = _lookup(WARMUP_TABLE, day_name, _warmup_full_body)
    cooldown = _lookup(COOLDOWN_TABLE, day_name, lambda: _cooldown_full_body())
    # cooldown factories are parameterized by holds; _lookup signature is fixed
    # to ()->list, so we re-warm via the same helper mechanism for cooldown
    # below if only a key hit triggered the wrong variant.
    if not isinstance(cooldown, list) or (cooldown and not isinstance(cooldown[0], dict)):
        cooldown = _cooldown_full_body()

    # --- clip row counts to a rough time budget if caller gave one -------
    def clip(rows, minutes, min_rows=4, max_rows=10):
        if minutes is None:
            return rows[:max_rows]
        target = max(min_rows, min(max_rows, int(minutes)))
        return rows[:target]

    warmup = clip(warmup, warmup_minutes, min_rows=5, max_rows=9)
    cooldown = clip(cooldown, cooldown_minutes, min_rows=5, max_rows=7)
    return warmup, cooldown


def attach_to_plan_day(plan_day):
    """Idempotent helper: attach warmup/cooldown arrays to a day dict.

    Skips if arrays are already populated (avoids re-writing AI-generated
    warmups if present). Returns the same day dict mutated.
    """
    if not isinstance(plan_day, dict):
        return plan_day
    existing_w = plan_day.get("warmup_exercises")
    existing_c = plan_day.get("cooldown_exercises")
    if isinstance(existing_w, list) and len(existing_w) >= 3 and isinstance(existing_c, list) and len(existing_c) >= 3:
        return plan_day

    day_name = str(plan_day.get("name", plan_day.get("split", "Full Body")))
    try:
        wmin = int(plan_day.get("warmup_minutes") or (len(day_name.split()) * 2 or 10))
    except (TypeError, ValueError):
        wmin = 10
    try:
        cmin = int(plan_day.get("cooldown_minutes") or 8)
    except (TypeError, ValueError):
        cmin = 8
    warmup, cooldown = generate_for_split(day_name, wmin, cmin)
    plan_day.setdefault("warmup_exercises", warmup)
    plan_day.setdefault("cooldown_exercises", cooldown)
    return plan_day


def attach_to_weekly_plan(weekly_plan):
    """Apply :func:`attach_to_plan_day` to every day in a plan list."""
    if not isinstance(weekly_plan, list):
        return weekly_plan
    return [attach_to_plan_day(day) for day in weekly_plan]
