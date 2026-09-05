import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infrastructure import storage
from application import data_loader

c = storage._get_supabase_client()
if c is None:
    raise SystemExit("client None")

# ==== Test A: load_all_user_data_for(FAKE uuid that matches no rows)
#  this should go into legacy fallback, pick the richest profile_id, and
#  return data from it (non-empty plan/history).
fake_uid = "00000000-0000-0000-0000-000000000000"
print("Test A: load_all_user_data_for(fake_uuid) should enter legacy fallback")
snap = storage.load_all_user_data_for(fake_uid)
assert snap is not None, "snap should not be None"
print(f"  profile_id returned: {snap.get('profile_id')!r}")
print(f"  profile isinstance(dict)={isinstance(snap.get('profile'),dict)} len keys={len(snap.get('profile') or {})}")
plan = snap.get("workout_plan")
print(f"  plan type={type(plan).__name__} isinstance(list)={isinstance(plan,list)} isinstance(dict)={isinstance(plan,dict)} len_if_iterable={len(plan) if isinstance(plan,(list,dict)) else 'N/A'}")
print(f"  workout_history isinstance(list)={isinstance(snap.get('workout_history'),list)} len={len(snap.get('workout_history') or [])}")
assert snap.get("profile_id") is not None, "profile_id must not be None (richest profile picked)"
# plan is either list or dict. history: len>0 because the database has 12 rows.
hist = snap.get("workout_history") or []
assert len(hist) > 0, f"expected history rows > 0, got {len(hist)}. Fix not working"
print("  -> PASS (legacy heuristic returned actual data)")

# ==== Test B: data_loader._load_user_data() returns proper plan (list of days) + history (list)
#  we call it with a fake user_id to force legacy fallback inside storage, which loads
#  same rich profile above.  This tests the plan coercion fix in data_loader.py.
print("\nTest B: _load_user_data returns plan coerced to list-of-days & non-empty history")
profile, plan2, hist2, pid2, src2 = data_loader._load_user_data(
    user_id=fake_uid,
    _profile_file=data_loader.DATA_DIR/"profile.json",
    _workout_plan_file=data_loader.DATA_DIR/"workout_plan.json",
    _workout_history_file=data_loader.DATA_DIR/"workout_history.json",
)
print(f"  storage_source = {src2!r}")
print(f"  profile_id returned = {pid2!r}")
print(f"  plan type={type(plan2).__name__} isinstance(list)={isinstance(plan2,list)} len={len(plan2) if isinstance(plan2,list) else 'N/A'}")
if isinstance(plan2, list) and plan2:
    print(f"    first plan item type={type(plan2[0]).__name__} keys_sample={sorted(list(plan2[0].keys())[:20]) if isinstance(plan2[0],dict) else 'N/A'}")
print(f"  history isinstance(list)={isinstance(hist2,list)} len={len(hist2)}")
assert isinstance(plan2, list), "plan must be a list after Credit #4 coercion fix"
assert isinstance(hist2, list) and len(hist2) > 0, "history must be list w/ len>0"
print("  -> PASS (data_loader plan coercion now outputs proper list-of-days)")
print("\nAll fixes GREEN. Historical data IS reachable now.")
