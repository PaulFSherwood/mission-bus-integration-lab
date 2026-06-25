from __future__ import annotations

from math import sin
from typing import Any

from .aircraft_truth import AircraftTruth


def weather_cells_for(truth: AircraftTruth) -> list[dict[str, Any]]:
    """Deterministic local simulated radar returns relative to ownship.

    Keeping the storm cells adapter-side means both cockpit radar and the large
    TAWS/Weather page can consume the same 1553 WEATHER_RADAR payload.
    """
    t = truth.timestamp or 0.0
    cells = [
        {
            "id": "WX01",
            "east_nm": 15.0 + sin(t * 0.010) * 2.0,
            "north_nm": 10.0 + sin(t * 0.008) * 1.5,
            "radius_nm": 12.0,
            "intensity": 0.55,
            "lightning": True,
        },
        {
            "id": "WX02",
            "east_nm": -20.0 + sin(t * 0.006) * 2.0,
            "north_nm": -8.0 + sin(t * 0.009) * 1.5,
            "radius_nm": 9.0,
            "intensity": 0.85,
            "lightning": True,
        },
        {
            "id": "WX03",
            "east_nm": 5.0 + sin(t * 0.012) * 1.0,
            "north_nm": -24.0 + sin(t * 0.007) * 1.0,
            "radius_nm": 7.0,
            "intensity": 0.35,
            "lightning": False,
        },
    ]
    return cells


def weather_radar_payload_for(truth: AircraftTruth, range_nm: float = 40.0) -> dict[str, Any]:
    cells = weather_cells_for(truth)
    severe = sum(1 for cell in cells if float(cell.get("intensity", 0.0)) >= 0.90)
    lightning = sum(1 for cell in cells if cell.get("lightning") and float(cell.get("intensity", 0.0)) > 0.50)
    return {
        "schema": "MBIL-WEATHER-RADAR-1",
        "mode": "SIM_ONLY",
        "range_nm": range_nm,
        "motion": "LOCAL_SIM",
        "cells": cells,
        "cell_count": len(cells),
        "severe_count": severe,
        "lightning_count": lightning,
        "valid": bool(truth.valid),
    }
