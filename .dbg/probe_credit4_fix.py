import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure import storage

c = storage._get_supabase_client()
if c is None:
    raise SystemExit(0)

print("== latest 2 profiles (raw top-level keys) ==")
r = c.table("profiles").select("*").order("created_at", desc=True).limit(2).execute()
for row in r.data:
    pid = row.get("id")
    print(f"\nid = {pid}")
    top_keys = sorted([k for k in row.keys() if k != "profile_data"])
    print(f"  top-level keys: {top_keys}")
    print(f"  row['user_id'] = {repr(row.get('user_id'))}")
    pd = row.get("profile_data")
    if isinstance(pd, dict):
        print(f"  profile_data isinstance(dict): OK, len(keys) = {len(pd)}")
        shown = 0
        for k, v in pd.items():
            if shown >= 25:
                print(f"    ... (+ {len(pd)-shown} more keys)")
                break
            shown += 1
            if isinstance(v, (dict, list)):
                rep = f"<{type(v).__name__} len={len(v)}>"
            else:
                rep = repr(v)[:80]
            print(f"    profile_data.{k} = {rep}")
    else:
        print(f"  profile_data type = {type(pd).__name__}")

    # probe plan + history for this profile id
    print(f"\n== workout_plans rows WHERE profile_id = {pid} ==")
    try:
        wp = c.table("workout_plans").select("id,created_at,plan_data") \
            .eq("profile_id", pid).order("created_at", desc=True).limit(3).execute()
        print(f"   rows count = {len(wp.data)}")
        for wp_row in wp.data[:2]:
            pdata = wp_row.get("plan_data")
            t = type(pdata).__name__
            size = len(pdata) if isinstance(pdata, (list, dict)) else "N/A"
            print(f"     plan id={wp_row.get('id')} created_at={wp_row.get('created_at')} type={t} len={size}")
    except Exception as e:
        print(f"   FAIL: {type(e).__name__}: {str(e)[:200]}")

    print(f"\n== workout_history rows WHERE profile_id = {pid} ==")
    try:
        wh = c.table("workout_history").select("id,workout_date,workout_data,workout_name") \
            .eq("profile_id", pid).order("workout_date", desc=True).limit(5).execute()
        print(f"   rows count = {len(wh.data)}")
        for wh_row in wh.data[:3]:
            wd = wh_row.get("workout_data")
            ex_n = len(wd.get("exercises", [])) if isinstance(wd, dict) else "?"
            print(f"     {wh_row.get('workout_date')} / name={wh_row.get('workout_name')!r} exercises={ex_n}")
    except Exception as e:
        print(f"   FAIL: {type(e).__name__}: {str(e)[:200]}")
