#!/usr/bin/env python3
# tools/xplane_probe.py
#
# Probe X-Plane 12 Web API datarefs and sample route/aircraft candidates.
# This tool does not connect MBIL yet. It only discovers what X-Plane exposes.

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8086/api/v3"
OUT_DIR = Path("data/xplane_probe")

ROUTE_KEYWORDS = [
    "fms", "flightplan", "flight_plan", "gps", "nav", "waypoint",
    "flightdir", "autopilot", "g430", "g530", "g1000",
]

AIRCRAFT_KEYWORDS = [
    "position", "latitude", "longitude", "elevation", "altitude",
    "indicated_airspeed", "true_airspeed", "groundspeed", "heading",
    "psi", "theta", "phi", "pitch", "roll", "vvi", "vertical",
    "fuel", "engine",
]

PREFERRED_DATAREFS = [
    "sim/flightmodel/position/latitude",
    "sim/flightmodel/position/longitude",
    "sim/flightmodel/position/elevation",
    "sim/flightmodel/position/y_agl",
    "sim/flightmodel/position/indicated_airspeed",
    "sim/flightmodel/position/true_airspeed",
    "sim/flightmodel/position/groundspeed",
    "sim/flightmodel/position/vh_ind_fpm",
    "sim/flightmodel/position/psi",
    "sim/flightmodel/position/theta",
    "sim/flightmodel/position/phi",
    "sim/flightmodel/weight/m_fuel_total",
    "sim/cockpit2/engine/indicators/engine_speed_rpm",
    "sim/cockpit2/engine/indicators/ITT_deg_C",
    "sim/cockpit2/engine/indicators/EGT_deg_C",
    "sim/cockpit2/radios/indicators/gps_bearing_deg_mag",
    "sim/cockpit2/radios/indicators/gps_dme_distance_nm",
    "sim/cockpit2/radios/indicators/gps_nav_id",
    "sim/cockpit2/radios/indicators/gps_nav_type",
    "sim/cockpit2/radios/indicators/gps_relative_bearing_deg",
    "sim/cockpit2/radios/indicators/gps_to_from",
]


def http_json(url: str, timeout: float = 5.0) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    return json.loads(text)


def get_datarefs(base_url: str) -> list[dict[str, Any]]:
    url = base_url.rstrip("/") + "/datarefs"
    result = http_json(url)
    if isinstance(result, dict):
        data = result.get("data", result.get("datarefs", []))
    else:
        data = result
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected /datarefs payload shape: {type(data).__name__}")
    return [item for item in data if isinstance(item, dict)]


def find_by_name(datarefs: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for ref in datarefs:
        if ref.get("name") == name:
            return ref
    return None


def get_ref_value(base_url: str, ref: dict[str, Any]) -> Any:
    ref_id = ref.get("id")
    return http_json(base_url.rstrip("/") + f"/datarefs/{ref_id}/value")


def filter_refs(datarefs: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
    matches = []
    for ref in datarefs:
        name = str(ref.get("name", "")).lower()
        if any(key.lower() in name for key in keywords):
            matches.append(ref)
    return matches


def sample_candidates(base_url: str, datarefs: list[dict[str, Any]], names: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name in names:
        ref = find_by_name(datarefs, name)
        if not ref:
            values[name] = {"found": False}
            continue
        try:
            value = get_ref_value(base_url, ref)
            values[name] = {
                "found": True,
                "id": ref.get("id"),
                "is_writable": ref.get("is_writable"),
                "value": value,
            }
        except Exception as exc:
            values[name] = {"found": True, "id": ref.get("id"), "error": str(exc)}
    return values


def sample_first_n(base_url: str, refs: list[dict[str, Any]], max_samples: int) -> list[dict[str, Any]]:
    samples = []
    for ref in refs[:max_samples]:
        item = {
            "id": ref.get("id"),
            "name": ref.get("name"),
            "is_writable": ref.get("is_writable"),
        }
        try:
            item["value"] = get_ref_value(base_url, ref)
        except Exception as exc:
            item["error"] = str(exc)
        samples.append(item)
    return samples


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--sample-values", action="store_true")
    parser.add_argument("--max-candidate-samples", type=int, default=40)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print(f"[XPlane Probe] Connecting to {base_url}")
    print(f"[XPlane Probe] Trying {base_url}/datarefs")

    try:
        datarefs = get_datarefs(base_url)
    except urllib.error.HTTPError as exc:
        print(f"[XPlane Probe] HTTP error: {exc.code} {exc.reason}")
        print(f"Try in browser: {base_url}/datarefs")
        return 1
    except Exception as exc:
        print(f"[XPlane Probe] Failed: {exc}")
        return 1

    print(f"[XPlane Probe] Found {len(datarefs)} datarefs")

    route_refs = filter_refs(datarefs, ROUTE_KEYWORDS)
    aircraft_refs = filter_refs(datarefs, AIRCRAFT_KEYWORDS)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "summary.json", {
        "base_url": base_url,
        "dataref_count": len(datarefs),
        "route_candidate_count": len(route_refs),
        "aircraft_candidate_count": len(aircraft_refs),
        "timestamp": time.time(),
    })
    write_json(OUT_DIR / "route_dataref_candidates.json", route_refs)
    write_json(OUT_DIR / "aircraft_dataref_candidates.json", aircraft_refs)
    write_json(OUT_DIR / "preferred_sample_values.json", sample_candidates(base_url, datarefs, PREFERRED_DATAREFS))

    if args.sample_values:
        print("[XPlane Probe] Sampling route candidates...")
        write_json(OUT_DIR / "route_candidate_sample_values.json", sample_first_n(base_url, route_refs, args.max_candidate_samples))
        print("[XPlane Probe] Sampling aircraft candidates...")
        write_json(OUT_DIR / "aircraft_candidate_sample_values.json", sample_first_n(base_url, aircraft_refs, args.max_candidate_samples))

    print("[XPlane Probe] Wrote:")
    for filename in [
        "summary.json",
        "route_dataref_candidates.json",
        "aircraft_dataref_candidates.json",
        "preferred_sample_values.json",
        "route_candidate_sample_values.json",
        "aircraft_candidate_sample_values.json",
    ]:
        path = OUT_DIR / filename
        if path.exists():
            print(f"  {path}")

    print()
    print("[XPlane Probe] Quick route search:")
    print(f"  grep -i 'flightplan\\|fms\\|waypoint\\|gps' {OUT_DIR / 'route_dataref_candidates.json'} | head -50")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
