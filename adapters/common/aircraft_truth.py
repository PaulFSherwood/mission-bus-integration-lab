from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Any


@dataclass
class AircraftTruth:
    """Adapter-side aircraft truth model.

    MBIL should not read this directly. The adapter converts this into
    1553/ARINC/discrete/analog style exchange files.
    """

    source: str = "SYNTHETIC"
    timestamp: float = 0.0
    lat: float = 30.47667
    lon: float = -87.18450
    altitude_ft: float = 9600.0
    airspeed_kts: float = 210.0
    heading_deg: float = 270.0
    vertical_speed_fpm: float = 0.0
    pitch_deg: float = 1.5
    roll_deg: float = 0.0
    yaw_deg: float = 0.0
    fuel_lbs: float = 5320.0
    engine_temp_c: float = 625.0
    oat_c: float = 12.0
    valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["timestamp"]:
            d["timestamp"] = time()
        return d

    @classmethod
    def from_mapping(cls, data: dict[str, Any], source: str = "EXTERNAL") -> "AircraftTruth":
        def num(name: str, default: float) -> float:
            value = data.get(name, default)
            try:
                return float(value)
            except Exception:
                return default

        return cls(
            source=str(data.get("source", source)),
            timestamp=num("timestamp", time()),
            lat=num("lat", cls.lat),
            lon=num("lon", cls.lon),
            altitude_ft=num("altitude_ft", data.get("altitude", cls.altitude_ft)),
            airspeed_kts=num("airspeed_kts", data.get("airspeed", cls.airspeed_kts)),
            heading_deg=num("heading_deg", data.get("heading", cls.heading_deg)),
            vertical_speed_fpm=num("vertical_speed_fpm", data.get("vs_fpm", cls.vertical_speed_fpm)),
            pitch_deg=num("pitch_deg", cls.pitch_deg),
            roll_deg=num("roll_deg", cls.roll_deg),
            yaw_deg=num("yaw_deg", data.get("heading_deg", cls.yaw_deg)),
            fuel_lbs=num("fuel_lbs", cls.fuel_lbs),
            engine_temp_c=num("engine_temp_c", cls.engine_temp_c),
            oat_c=num("oat_c", cls.oat_c),
            valid=bool(data.get("valid", True)),
        )
