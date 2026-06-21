#!/usr/bin/env python3
"""
Summarize data/travel_times.csv into a travel-time table bucketed by
(route, day-of-week, hour-of-day). Pure stdlib; prints a table and writes
summary.csv.

Buckets are kept at the finest grain (each weekday's hour is its own bucket, so
Mon 18:00 != Tue 18:00). To get coarser views (e.g. all weekdays, or a wider
time-of-day band) just union the relevant buckets from the raw data.

Usage: python analyze.py
"""
import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "data", "travel_times.csv")
OUT_PATH = os.path.join(HERE, "summary.csv")

# Percentiles to report. p50 = typical trip; p80 = FHWA LOTTR reliability basis;
# p95 = Planning Time Index ("budget to be on time 19 days in 20"); p10 = observed
# near-free-flow floor; p90/p99 fill in the tail. p95/p99 need a deep bucket to
# mean anything -- read them alongside n.
PCTS = [10, 50, 80, 90, 95, 99]

# Sort order for day-of-week (collect.py writes %a abbreviations).
DOW_ORDER = {d: i for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])}


# Expected one-way road distance for this segment (~1.5 km). A reading far from
# this usually means Google snapped to the wrong side and routed a U-turn, which
# would inflate travel time. We flag it rather than silently averaging it in.
EXPECTED_DIST_M = 1500
DIST_TOLERANCE = 0.20   # 20%


def out_of_tolerance(dist_m):
    return abs(dist_m - EXPECTED_DIST_M) > EXPECTED_DIST_M * DIST_TOLERANCE


def check_distance(distances, excluded):
    if not distances:
        return
    s = sorted(distances)
    med = s[len(s) // 2]
    lo, hi = s[0], s[-1]
    print(f"Route integrity: distance median {med/1000:.2f} km "
          f"(range {lo/1000:.2f}-{hi/1000:.2f} km, expected ~{EXPECTED_DIST_M/1000:.1f} km)")
    if excluded:
        print(f"  WARNING: excluded {excluded}/{len(distances)} readings that differ "
              f"from {EXPECTED_DIST_M/1000:.1f} km by more than {int(DIST_TOLERANCE*100)}% "
              f"(likely wrong-side snap / U-turn); they are not counted in the stats below.")
    print()


def pct(values_sorted, p):
    """Percentile via linear interpolation between ranks (NumPy 'linear'/type-7)."""
    s = values_sorted
    if not s:
        return None
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main():
    if not os.path.exists(CSV_PATH):
        print("No data yet. Run collect.py (or wait for the GitHub Action) first.")
        return

    # bucket[(route, dow, hour)] = [durations_sec]
    buckets = defaultdict(list)
    distances = []   # metres, for the route-integrity check
    excluded = 0
    with open(CSV_PATH) as f:
        for r in csv.DictReader(f):
            if r["status"] != "ok" or not r["duration_sec"]:
                continue
            dm = int(r["distance_m"]) if r.get("distance_m") else None
            if dm is not None:
                distances.append(dm)
                if out_of_tolerance(dm):
                    excluded += 1
                    continue   # wrong-snap route: do not count in travel-time stats
            key = (r["route_id"], r["dow"], int(r["hour_ist"]))
            buckets[key].append(int(r["duration_sec"]))

    check_distance(distances, excluded)

    if not buckets:
        print("No successful samples yet.")
        return

    pct_headers = [f"p{p}" for p in PCTS]
    header = f"{'route':<22} {'day':<4} {'hr':>3} {'n':>4} " + \
        " ".join(f"{h:>6}" for h in pct_headers)
    print(header)
    print("-" * len(header))

    out_rows = []
    # Sort by route, then weekday order, then hour.
    for key in sorted(buckets, key=lambda k: (k[0], DOW_ORDER.get(k[1], 9), k[2])):
        route, dow, hour = key
        s = sorted(buckets[key])
        pvals_min = [pct(s, p) / 60 for p in PCTS]  # seconds -> minutes
        print(f"{route:<22} {dow:<4} {hour:>3} {len(s):>4} " +
              " ".join(f"{v:>6.1f}" for v in pvals_min))
        row = {"route_id": route, "dow": dow, "hour_ist": hour, "n_samples": len(s)}
        for p, v in zip(PCTS, pvals_min):
            row[f"p{p}_min"] = round(v, 2)
        out_rows.append(row)

    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWrote {OUT_PATH} ({len(out_rows)} buckets). "
          f"Total samples: {sum(len(v) for v in buckets.values())}")


if __name__ == "__main__":
    main()
