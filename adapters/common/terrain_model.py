# adapters/common/terrain_model.py
from __future__ import annotations

import math
from typing import Any

from adapters.common.aircraft_truth import AircraftTruth
from adapters.common.terrain_grid import lat_lon_from_offset, terrain_elevation_ft


def terrain_level_from_clearance(clearance_ft: float) -> str:
    if clearance_ft <= 300.0:
        return "red"
    if clearance_ft <= 1000.0:
        return "yellow"
    return "green"


def alert_state_from_clearance(clearance_ft: float) -> str:
    if clearance_ft <= 300.0:
        return "TERRAIN PULL UP"
    if clearance_ft <= 1000.0:
        return "CAUTION TERRAIN"
    return "CLEAR"


def _truth_float(truth: Any, name: str, default: float = 0.0) -> float:
    if isinstance(truth, dict):
        value = truth.get(name, default)
    else:
        value = getattr(truth, name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _truth_bool(truth: Any, name: str, default: bool = True) -> bool:
    if isinstance(truth, dict):
        return bool(truth.get(name, default))
    return bool(getattr(truth, name, default))


def taws_payload_for(
    truth: AircraftTruth,
    range_nm: float = 40.0,
    sample_step_nm: float = 4.0,
) -> dict[str, Any]:
    """Build a complete, drawable TAWS payload from aircraft truth.

    The adapter owns this. MBIL should draw these returns instead of inventing
    terrain in the browser.
    """
    aircraft_lat = _truth_float(truth, "lat", 30.5)
    aircraft_lon = _truth_float(truth, "lon", -87.2)
    aircraft_alt_ft = _truth_float(truth, "altitude_ft", 9500.0)

    terrain_under = terrain_elevation_ft(aircraft_lat, aircraft_lon)
    clearance = aircraft_alt_ft - terrain_under

    worst_clearance = clearance
    worst_terrain = terrain_under
    worst_point: dict[str, float] = {
        "lat": round(aircraft_lat, 6),
        "lon": round(aircraft_lon, 6),
        "east_nm": 0.0,
        "north_nm": 0.0,
    }

    terrain_returns: list[dict[str, Any]] = []
    steps = max(1, int(range_nm // sample_step_nm))

    for east_i in range(-steps, steps + 1):
        for north_i in range(-steps, steps + 1):
            east_nm = east_i * sample_step_nm
            north_nm = north_i * sample_step_nm
            distance_nm = math.sqrt(east_nm * east_nm + north_nm * north_nm)

            if distance_nm > range_nm:
                continue

            lat, lon = lat_lon_from_offset(aircraft_lat, aircraft_lon, east_nm, north_nm)
            terrain = terrain_elevation_ft(lat, lon)
            point_clearance = aircraft_alt_ft - terrain

            if point_clearance < worst_clearance:
                worst_clearance = point_clearance
                worst_terrain = terrain
                worst_point = {
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "east_nm": round(east_nm, 2),
                    "north_nm": round(north_nm, 2),
                }

            terrain_returns.append(
                {
                    "east_nm": round(east_nm, 2),
                    "north_nm": round(north_nm, 2),
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "elevation_ft": round(terrain, 1),
                    "clearance_ft": round(point_clearance, 1),
                    "level": terrain_level_from_clearance(point_clearance),
                }
            )

    alert_state = alert_state_from_clearance(min(clearance, worst_clearance))

    return {
        "schema": "MBIL-TAWS-DATA-1",
        "mode": "SIM_ONLY",
        "range_nm": range_nm,
        "sample_step_nm": sample_step_nm,
        "terrain_source": "PGM_TERRAIN_GRID_OR_SYNTHETIC_FALLBACK",
        "terrain_under_ft": round(terrain_under, 1),
        "terrain_under_aircraft_ft": round(terrain_under, 1),
        "clearance_ft": round(clearance, 1),
        "worst_clearance_ft": round(worst_clearance, 1),
        "worst_terrain_ft": round(worst_terrain, 1),
        "worst_point": worst_point,
        "alert_state": alert_state,
        "aircraft_altitude_ft": round(aircraft_alt_ft, 1),
        "terrain_return_count": len(terrain_returns),
        "terrain_returns": terrain_returns,
        "valid": _truth_bool(truth, "valid", True),
    }
