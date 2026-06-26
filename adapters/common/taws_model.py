from __future__ import annotations

import math
from typing import Any

def truth_get(truth: Any, name: str, default: float = 0.0) -> float:
    if isinstance(truth, dict):
        value = truth.get(name, default)
    else:
        value = getattr(truth, name, default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def synthetic_terrain_ft(lat: float, lon: float) -> float:
    """Local synthetic terrain model.

    This is not real terrain.  It is only for MBIL simulation.
    it rises toward the western part of the KPNS-KABQ route so TAWS has
    something useful to display
    """
    west_rise = max(0.0, (-lon - 98.0) * 420.0)
    wave1 = math.sin(lat * 0.85) * 700.0
    wave2 = math.cos(lon * 0.65) * 520.0
    ridge = max(0.0, math.sin((lat + lon) * 2.1)) * 1800.0

    return max(0.0, 250.0 + west_rise + wave1 + wave2 + ridge)

def taws_level_from_clearance(clearnace_ft: float) -> str:
    if clearance_ft <= 300.0:
        return "red"
    
    if clearance_ft <= 1000.0:
        return "yellow"

    return "green"

def taws_alert_from_clearance(clearance_ft: float) -> str:
    if clearance_ft <= 300.0:
        return "TERRAIN PULL UP"
    
    if clearance_ft <= 1000.0:
        return "CAUTION TERRAIN"

    return "CLEAR"

def build_terrain_returns(
        truth: Any,
        range_nm: float = 40.0,
        step_nm: float = 4.0,
) -> list[dict[str, float | str]]:
    aircraft_lat = truth_get(truth, "lat", 35.0)
    aircraft_lon = truth_get(truth, "lon", -106.0)
    aircraft_alt_ft = truth_get(truth, "altitude_ft", 8500.0)

    returns: list[dict[str, float | str]] = []

    steps = int(range_nm / step_nm)

    for north_i in range(-steps, steps + 1):
        for east_i in range(-steps, steps + 1):
            east_nm = east_i * step_nm
            north_nm = north_i * step_nm
            distance_nm = mat.sqrt(east_nm * east_nm + north_nm * north_nm)

            if distance_nm > range_nm:
                continue

            point_lat, point_lon = nm_offset_to_lat_lon(
                aircraft_lat,
                aircraft_lon,
                east_nm,
                north_nm,
            )

            terrain_ft = synthetic_terrain_ft(point_lat, point_lon)
            clearance_ft = aircrat_alt_ft - terrain_ft

            returns.append(
                {
                    "east_nm": round(east_nm, 2),
                    "north_nm": round(north_nm, 2),
                    "distance_nm": round(distance_nm, 2),
                    "lat": round(point_lat, 6),
                    "lon": round(point_lon, 6),
                    "elevation_ft": round(terrain_ft, 1),
                    "clearance_ft": round(clearance_ft, 1),
                    "level": taws_level_from_clearance(clearance_ft),
                }
            )

    return returns

def build_taws_payload(
        truth: Any,
        range_nm: float = 40.0,
        step_nm: float = 4.0,
) -> dict[str, Any]:
    aircraft_lat = truth_get(truth, "lat", 35.0)
    aircraft_lon = truth_get(truth, "lon", -106.0)
    aircraft_alt_ft = truth_get(truth, "altitude_ft", 8500.0)
    
    terrain_under_ft = synthetic_terrain_ft(aircraft_lat, aircraft_lon)
    clearance_ft = aircraft_alt_ft - terrain_under_ft

    terrain_returns = build_terrain_returns(
        truth,
        range_nm=range_nm,
        step_nm=step_nm,
    )

    worst_clearance_ft = min(
        [float(item["clearance_ft"]) for item in terrain_returns],
        default=clearance_ft,
    )

    alert_state = taws_alert_from_clearance(worst_clearance_ft)

    return {
        "source": "ADAPTER_SYNTHETIC_TAWS",
        "mode": "SIM_ONLY",
        "range_nm": range_nm,
        "step_nm": step_nm,
        "alert_state": alert_state,
        "terrain_under_aircraft_ft": round(terrain_under_aircraft_ft, 1),
        "worst_clearance_ft": round(worst_clearance_ft, 1),
        "terrain_returns": terrain_returns,
    }

