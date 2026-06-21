#!/usr/bin/env python3
"""
Poll the Google Routes API for travel time between configured points, in both
directions, and append one row per direction to data/travel_times.csv.

Uses only the Python standard library (no pip install needed in CI).
Requires env var GOOGLE_MAPS_API_KEY.
"""
import csv
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "data", "travel_times.csv")
IST = timezone(timedelta(hours=5, minutes=30))  # log local Mumbai time for analysis

FIELDS = [
    "ts_utc", "ts_ist", "dow", "hour_ist", "route_id",
    "origin_name", "dest_name",
    "duration_sec", "static_duration_sec", "distance_m", "tti", "status",
]


def query_route(api_key, origin, dest):
    """Return (duration_sec, static_duration_sec, distance_m) or raise."""
    body = {
        "origin": {"location": {"latLng": {"latitude": origin["lat"], "longitude": origin["lng"]}}},
        "destination": {"location": {"latLng": {"latitude": dest["lat"], "longitude": dest["lng"]}}},
        "travelMode": "DRIVE",
        # TRAFFIC_AWARE_OPTIMAL = best live-traffic estimate. departureTime defaults to "now".
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            # staticDuration = free-flow time (no traffic) -> lets us compute congestion index.
            "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    route = data["routes"][0]
    dur = int(str(route["duration"]).rstrip("s"))
    static = int(str(route.get("staticDuration", route["duration"])).rstrip("s"))
    dist = int(route["distanceMeters"])
    return dur, static, dist


def main():
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_MAPS_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    with open(os.path.join(HERE, "config.json")) as f:
        config = json.load(f)

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(IST)
    rows = []

    for route in config["routes"]:
        origin, dest = route["origin"], route["destination"]
        row = {
            "ts_utc": now_utc.isoformat(timespec="seconds"),
            "ts_ist": now_ist.isoformat(timespec="seconds"),
            "dow": now_ist.strftime("%a"),
            "hour_ist": now_ist.hour,
            "route_id": route["id"],
            "origin_name": origin["name"],
            "dest_name": dest["name"],
        }
        try:
            dur, static, dist = query_route(api_key, origin, dest)
            row.update({
                "duration_sec": dur,
                "static_duration_sec": static,
                "distance_m": dist,
                "tti": round(dur / static, 3) if static else "",
                "status": "ok",
            })
        except urllib.error.HTTPError as e:
            row.update({"duration_sec": "", "static_duration_sec": "", "distance_m": "",
                        "tti": "", "status": f"http_{e.code}"})
            print(f"HTTPError {e.code}: {e.read().decode('utf-8', 'replace')[:300]}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001 - keep collecting other routes
            row.update({"duration_sec": "", "static_duration_sec": "", "distance_m": "",
                        "tti": "", "status": f"err_{type(e).__name__}"})
            print(f"Error: {e}", file=sys.stderr)
        rows.append(row)

    new_file = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if r["status"] == "ok")
    print(f"Logged {len(rows)} rows ({ok} ok) at {now_ist.isoformat(timespec='seconds')} IST")


if __name__ == "__main__":
    main()
