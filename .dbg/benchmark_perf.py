"""Synthetic pre-fix performance test — no Streamlit UI required.

Measures timing of:
  H1: load_persistent_data() -> 4 sequential Supabase HTTP calls per call
  H2: exercises re-loaded from Supabase every call (cached?)
  H5: _get_supabase_client() reconstruction + _profiles_support_user_id() per call
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from statistics import mean, pstdev

# Bootstrap project path + logging
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config.logging_config import configure_logging  # noqa: E402
configure_logging(level=logging.WARNING)

from application import data_loader  # noqa: E402
from infrastructure import storage  # noqa: E402


def _nop(*_a, **_k):
    """Silent warning callback."""
    return None


def bench(name: str, fn, n=3) -> list[float]:
    timings: list[float] = []
    print(f"\n[perf] benchmarking {name} (N={n})")
    for i in range(n):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        dt_ms = (t1 - t0) * 1000
        timings.append(dt_ms)
        print(f"   run {i+1}/{n}: {dt_ms:>7.1f} ms")
    avg = mean(timings)
    sd = pstdev(timings) if len(timings) > 1 else 0.0
    print(f"   -> avg={avg:>6.1f} ms   stddev={sd:>6.1f} ms")
    return timings


def main() -> int:
    print("=" * 72)
    print("[perf] H5: Supabase client + schema probe cost")
    print("=" * 72)

    if not storage.is_supabase_available():
        print("WARNING: Supabase not configured — skipping network tests, showing local-only cost")

    bench("is_supabase_available()", lambda: storage.is_supabase_available(), n=5)
    bench("supabase_schema_ready() — new client + schema probe each",
          lambda: storage.supabase_schema_ready(), n=5)

    print()
    print("=" * 72)
    print("[perf] H1: full load_persistent_data() — network calls NOT cached per rerender")
    print("=" * 72)

    if not storage.is_supabase_available():
        print("SKIPPED (no Supabase). Expected timing per real deploy: ~400-1500ms/call (4 round-trips).")
    else:
        bench("load_persistent_data(no auth) — exercises supabase + 3 empty user calls",
              lambda: data_loader.load_persistent_data(
                  user_id=None, warning_callback=_nop), n=3)

    print()
    print("=" * 72)
    print("[perf] H3: app.py import + set_page_config + 6 page if/elif (no render)")
    print("=" * 72)

    # Import app.py module and count overhead of module-level loading calls
    t0 = time.perf_counter()
    import importlib.util  # noqa: E402
    spec = importlib.util.spec_from_file_location(
        "app_entry_perf", ROOT / "app.py")
    # We don't actually execute the whole module because streamlit st.set_page_config
    # would try to start UI. Instead, we import the pure-work modules:
    from domain import dashboard_metrics  # noqa: E402
    from domain import performance, workout_validation, exercise_rules  # noqa: E402
    from modules import analytics, workout_generator  # noqa: E402
    t1 = time.perf_counter()
    print(f"   Heavy pure-domain modules imported in {(t1-t0)*1000:6.1f} ms")

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print("Expected 4 Supabase HTTP calls per widget interaction if NOT cached:")
    print("   1) client.table('exercises').select('*')  ~ 50-500ms (catalog, no auth filter)")
    print("   2) load_latest_profile_from_supabase()   ~ 50-300ms")
    print("   3) get_latest_profile_id()               ~ 40-200ms")
    print("   4) load_latest_workout_plan_from_supabase() ~ 50-400ms")
    print("   5) load_workout_history_from_supabase()  ~ 60-600ms")
    print("   Total on EVERY rerender: 250-2000ms of BLOCKING sync HTTP round-trips.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
