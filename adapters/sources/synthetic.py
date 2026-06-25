from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from time import time

from adapters.common.aircraft_truth import AircraftTruth


def _parse_latlon_token(ns_token: str, ew_token: str) -> tuple[float, float]:
    # Input route lines look like: KPNS GPS N30 28.60 W87 11.07
    raise NotImplementedError


def load_route_points(route_path: str = "data/routes/kpns_kabq_points.txt") -> list[tuple[str, float, float]]:
    path = Path(route_path)
    if not path.exists():
        return [
            ("KPNS", 30.47667, -87.18450),
            ("KABQ", 35.04100, -106.60983),
        ]

    points: list[tuple[str, float, float]] = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        ident = parts[0]
        try:
            ns = parts[2]
            ns_min = float(parts[3])
            ew = parts[4]
            ew_min = float(parts[5])
            lat = float(ns[1:]) + ns_min / 60.0
            lon = float(ew[1:]) + ew_min / 60.0
            if ns[0].upper() == "S":
                lat *= -1.0
            if ew[0].upper() == "W":
                lon *= -1.0
            points.append((ident, lat, lon))
        except Exception:
            continue

    return points or [("KPNS", 30.47667, -87.18450), ("KABQ", 35.04100, -106.60983)]


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    y = sin(radians(lon2 - lon1)) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
    return (atan2(y, x) * 180.0 / 3.141592653589793 + 360.0) % 360.0


class SyntheticAircraftSource:
    name = "Synthetic Aircraft Source"

    def __init__(self, route_path: str = "data/routes/kpns_kabq_points.txt"):
        self.route = load_route_points(route_path)
        self.leg = 0
        self.leg_fraction = 0.0
        self.airspeed_kts = 240.0
        self.altitude_ft = 9600.0
        self.last_time = time()
        self.tick = 0

    def online(self) -> bool:
        return True

    def next_truth(self) -> AircraftTruth:
        now = time()
        dt = max(0.0, min(2.0, now - self.last_time))
        self.last_time = now
        self.tick += 1

        if len(self.route) < 2:
            return AircraftTruth(source="SYNTHETIC", timestamp=now)

        # Simple route progress. Roughly one leg per few minutes for display purposes.
        self.leg_fraction += dt * 0.006
        if self.leg_fraction >= 1.0:
            self.leg_fraction = 0.0
            self.leg = (self.leg + 1) % (len(self.route) - 1)

        a = self.route[self.leg]
        b = self.route[self.leg + 1]
        f = self.leg_fraction
        lat = a[1] + (b[1] - a[1]) * f
        lon = a[2] + (b[2] - a[2]) * f
        hdg = _bearing_deg(a[1], a[2], b[1], b[2])

        # Small motion values so the cockpit is alive.
        roll = sin(now * 0.35) * 4.0
        pitch = 1.5 + sin(now * 0.20) * 1.0
        vs = sin(now * 0.15) * 250.0
        fuel = max(700.0, 5320.0 - self.tick * 0.7)

        return AircraftTruth(
            source="SYNTHETIC",
            timestamp=now,
            lat=lat,
            lon=lon,
            altitude_ft=self.altitude_ft + sin(now * 0.08) * 500.0,
            airspeed_kts=self.airspeed_kts + sin(now * 0.18) * 8.0,
            heading_deg=hdg,
            vertical_speed_fpm=vs,
            pitch_deg=pitch,
            roll_deg=roll,
            yaw_deg=hdg,
            fuel_lbs=fuel,
            engine_temp_c=625.0 + sin(now * 0.11) * 18.0,
            oat_c=12.0,
            valid=True,
        )
