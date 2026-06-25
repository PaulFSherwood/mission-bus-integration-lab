from __future__ import annotations

from math import cos, sin
from typing import Any

from .aircraft_truth import AircraftTruth


def synthetic_terrain_ft(lat: float, lon: float) -> float:
    """Local simulation terrain model shared by adapter and displays.

    This is not real terrain data. It is a deterministic stand-in until SRTM or
    Copernicus DEM tile lookup is added under the same function name.
    """
    west_rise = max(0.0, (-lon - 98.0) * 420.0)
    wave1 = sin(lat * 0.85) * 700.0
    wave2 = cos(lon * 0.65) * 520.0
    ridge = max(0.0, sin((lat + lon) * 2.1)) * 1800.0
    return max(0.0, 250.0 + west_rise + wave1 + wave2 + ridge)


def alert_from_clearance(clearance_ft: float) -> str:
    if clearance_ft <= 300.0:
        return "TERRAIN PULL UP"
    if clearance_ft <= 1000.0:
        return "CAUTION TERRAIN"
    return "CLEAR"


def lat_lon_from_offset(lat: float, lon: float, east_nm: float, north_nm: float) -> tuple[float, float]:
    avg_lat_rad = lat * 3.141592653589793 / 180.0
    out_lat = lat + north_nm / 60.0
    out_lon = lon + east_nm / (60.0 * cos(avg_lat_rad))
    return out_lat, out_lon


def taws_payload_for(truth: AircraftTruth, range_nm: float = 40.0, sample_step_nm: float = 5.0) -> dict[str, Any]:
    terrain_under = synthetic_terrain_ft(truth.lat, truth.lon)
    clearance = truth.altitude_ft - terrain_under
    worst_clearance = clearance
    worst_terrain = terrain_under
    worst_point = {"lat": truth.lat, "lon": truth.lon, "east_nm": 0.0, "north_nm": 0.0}

    steps = int(range_nm // sample_step_nm)
    for east_i in range(-steps, steps + 1):
        for north_i in range(-steps, steps + 1):
            east_nm = east_i * sample_step_nm
            north_nm = north_i * sample_step_nm
            if (east_nm * east_nm + north_nm * north_nm) ** 0.5 > range_nm:
                continue
            lat, lon = lat_lon_from_offset(truth.lat, truth.lon, east_nm, north_nm)
            terrain = synthetic_terrain_ft(lat, lon)
            point_clearance = truth.altitude_ft - terrain
            if point_clearance < worst_clearance:
                worst_clearance = point_clearance
                worst_terrain = terrain
                worst_point = {"lat": lat, "lon": lon, "east_nm": east_nm, "north_nm": north_nm}

    return {
        "schema": "MBIL-TAWS-DATA-1",
        "mode": "SIM_ONLY",
        "range_nm": range_nm,
        "terrain_source": "SYNTHETIC_LOCAL_TERRAIN",
        "terrain_under_ft": round(terrain_under, 1),
        "terrain_under_aircraft_ft": round(terrain_under, 1),
        "clearance_ft": round(clearance, 1),
        "worst_clearance_ft": round(worst_clearance, 1),
        "worst_terrain_ft": round(worst_terrain, 1),
        "worst_point": worst_point,
        "alert_state": alert_from_clearance(min(clearance, worst_clearance)),
        "aircraft_altitude_ft": round(truth.altitude_ft, 1),
        "valid": bool(truth.valid),
    }
