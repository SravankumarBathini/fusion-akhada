import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infrastructure import storage
c = storage._get_supabase_client()
if c is None: raise SystemExit(0)

# ======= 1) find ALL profile IDs that have workout_history =======
wh_all = c.table("workout_history").select("profile_id,id,workout_date").execute()
print("workout_history total rows =", len(wh_all.data) if wh_all else 0)
pid_hist = {}
for row in (wh_all.data or []):
    pid_hist[row["profile_id"]] = pid_hist.get(row["profile_id"], 0) + 1
print("profile_ids that HAVE history workouts (top 20):")
for i,(pid, cnt) in enumerate(sorted(pid_hist.items(), key=lambda kv: -kv[1])[:20], 1):
    print(f"  {i:2d}. {pid} -> {cnt} workouts")

wp_all = c.table("workout_plans").select("profile_id,id").execute()
print("\nworkout_plans total rows =", len(wp_all.data) if wp_all else 0)
pid_plan = {}
for row in (wp_all.data or []):
    pid_plan[row["profile_id"]] = pid_plan.get(row["profile_id"], 0) + 1
print("profile_ids that HAVE workout_plans (top 20):")
for i,(pid, cnt) in enumerate(sorted(pid_plan.items(), key=lambda kv: -kv[1])[:20], 1):
    print(f"  {i:2d}. {pid} -> {cnt} plans")

# ======= 2) for each such history profile_id: fetch profile row, print schema =======
interesting = sorted(set(pid_hist) | set(pid_plan))
print(f"\n=== {len(interesting)} distinct profile IDs with plan/history ===\n")
for pid in interesting[:8]:
    r = c.table("profiles").select("*").eq("id", pid).execute()
    if not r or not r.data:
        print(f"  {pid}: NO ROW in profiles")
        continue
    row = r.data[0]
    user_id = row.get("user_id")
    top_keys = sorted([k for k in row.keys() if k not in ["profile_data","id","created_at","updated_at"]])
    pd = row.get("profile_data")
    is_pd_dict = isinstance(pd, dict)
    pd_keys_count = len(pd) if is_pd_dict else 0
    print(f"  pid={pid}")
    print(f"    profiles.user_id = {repr(user_id)}")
    print(f"    has plan rows={pid_plan.get(pid,0)} has hist rows={pid_hist.get(pid,0)}")
    print(f"    top-level columns present (schema B style): {len(top_keys)}")
    print(f"      top 10 of {len(top_keys)}: {top_keys[:10]}")
    print(f"    profile_data isinstance(dict) = {is_pd_dict}, keys count = {pd_keys_count}")
    if is_pd_dict:
        print(f"      sample keys: {sorted(list(pd.keys()))[:15]}")
        for key in ['id','user_id','auth_user_id','email','uid']:
            if key in pd: print(f"        profile_data.{key} = {repr(pd[key])[:60]}")
    print()

# ======= 3) Confirm that Credit #4 SQL at 003 returns for an old profile ID (schema A) ======
if interesting:
    sample_pid = max(interesting, key=lambda p: pid_hist.get(p,0)+pid_plan.get(p,0))
    print(f"=== Directly inspecting MOST-POPULATED profile_id with hist+plan = {sample_pid}")
    # fetch user_id of that row
    r = c.table("profiles").select("id,user_id").eq("id", sample_pid).execute()
    sample_user_id = r.data[0].get("user_id") if r and r.data else None
    print(f"  profiles.user_id = {repr(sample_user_id)}")
    if sample_user_id:
        try:
            rr = c.rpc("get_user_snapshot", {"user_id_in": sample_user_id}).execute()
            payload = getattr(rr, "data", None)
            if isinstance(payload, list) and payload:
                payload = payload[0]
            print(f"  RPC isinstance(dict)={isinstance(payload, dict)}")
            if isinstance(payload, dict):
                for k in ["profile_id","profile","workout_plan","workout_history"]:
                    v = payload.get(k)
                    if k == "workout_history":
                        print(f"    {k}: is_list={isinstance(v,list)} len={len(v) if isinstance(v,list) else 'N/A'}")
                        if isinstance(v, list) and v:
                            first = v[0]
                            print(f"      first item type={type(first).__name__} keys count={len(first) if isinstance(first,dict) else 'N/A'} has_workout_data={'workout_data' in first if isinstance(first,dict) else 'N/A'}")
                    elif k == "workout_plan":
                        print(f"    {k}: type={type(v).__name__} islist={isinstance(v,list)} size={len(v) if isinstance(v,(list,dict)) else 'N/A'}")
                    else:
                        x = v if not isinstance(v, dict) else f"<dict {len(v)} keys>"
                        print(f"    {k}: {str(x)[:120]}")
        except Exception as e:
            print(f"  RPC FAILED: {type(e).__name__}: {str(e)[:400]}")
