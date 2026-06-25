from __future__ import annotations

from math import atan2, cos, radians, sin
from pathlib import Path
from time import time

from adapters.common.aircraft_truth import AircraftTruth


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
        if len(parts) < 6:
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

    def __init__(self, route_path: str = "data/routes/kpns_kabq_points.txt", profile: str = "normal"):
        self.route = load_route_points(route_path)
        self.leg = 0
        self.leg_fraction = 0.0
        self.airspeed_kts = 240.0
        self.profile = profile
        self.altitude_ft = self._altitude_for_profile(profile)
        self.last_time = time()
        self.tick = 0
        self.route_name = "KPNS-KABQ"

    @staticmethod
    def _altitude_for_profile(profile: str) -> float:
        profile = (profile or "normal").strip().lower()
        if profile in {"terrain-caution", "caution"}:
            return 4000.0
        if profile in {"terrain-pull-up", "pull-up", "pullup"}:
            return 3000.0
        if profile in {"low-level", "low"}:
            return 5000.0
        return 9600.0

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
        heading = _bearing_deg(a[1], a[2], b[1], b[2])

        # Gentle values so cockpit instruments visibly move.
        alt = self.altitude_ft + sin(now * 0.04) * 350.0
        speed = self.airspeed_kts + sin(now * 0.07) * 12.0
        vs = sin(now * 0.05) * 450.0
        fuel = max(500.0, 5320.0 - self.tick * 0.25)

        return AircraftTruth(
            source=f"SYNTHETIC:{self.profile}",
            timestamp=now,
            route=self.route_name,
            current_wp=a[0],
            next_wp=b[0],
            lat=lat,
            lon=lon,
            altitude_ft=alt,
            airspeed_kts=speed,
            heading_deg=heading,
            vertical_speed_fpm=vs,
            pitch_deg=2.0 + sin(now * 0.09),
            roll_deg=sin(now * 0.06) * 8.0,
            yaw_deg=heading,
            fuel_lbs=fuel,
            engine_temp_c=625.0 + sin(now * 0.03) * 20.0,
            oat_c=12.0 + sin(now * 0.02) * 5.0,
            valid=True,
        )
