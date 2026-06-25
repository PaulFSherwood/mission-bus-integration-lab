from __future__ import annotations

from math import cos, sin

def synthetic_terrain_ft(lat: float, lon: float) -> float:
    """Fallback terrain model for local simulation when DEM files are unavailable."""
    west_rise = max(0.0, (-lon - 98.0) * 420.0)
    wave1 = sin(lat * 0.85) * 700.0
    wave2 = cos(lon * 0.65) * 520.0
    ridge = max(0.0, sin((lat+ lon) * 2.1)) * 1800.0

    return max(0.0, 250.0 + west_rise + wave1 + wave2 + ridge)

def elevation_lookup_ft(lat: float, lon: float) -> float:
    """Terrain lookup entry point.

        Phase 1 uses synthetic local terrain. Later this can be replaced with
        SRTM/Copernicus DEM tile lookup from data/dem without changing the UI.
    """
    return synthetic_terrain_ft(lat, lon)
