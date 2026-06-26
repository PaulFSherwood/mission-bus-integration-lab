from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from pathlib import Path
from time import time
from typing import Any

from adapters.common.aircraft_truth import AircraftTruth

M_TO_FT = 3.280839895
MPS_TO_KTS = 1.9438444924
KG_TO_LB = 2.2046226218

DEFAULT_BASE_URL = "http://127.0.0.1:8086/api/v3"

DATAREFS = {
    "lat": "sim/flightmodel/position/latitude",
    "lon": "sim/flightmodel/position/longitude",
    "elevation_m": "sim/flightmodel/position/elevation",
    "agl_m": "sim/flightmodel/position/y_agl",
    "ias_kts": "sim/flightmodel/position/indicated_airspeed",
    "tas_mps": "sim/flightmodel/position/true_airspeed",
    "gs_mps": "sim/flightmodel/position/groundspeed",
    "vs_fpm": "sim/flightmodel/position/vh_ind_fpm",
    "heading_deg": "sim/flightmodel/position/psi",
    "pitch_deg": "sim/flightmodel/position/theta",
    "roll_deg": "sim/flightmodel/position/phi",
    "fuel_kg": "sim/flightmodel/weight/m_fuel_total",
    "engine_rpm": "sim/cockpit2/engine/indicators/engine_speed_rpm",
    "engine_egt_c": "sim/cockpit2/engine/indicators/EGT_deg_C",
    "engine_itt_c": "sim/cockpit2/engine/indicators/ITT_deg_C",
    "gps_bearing_deg": "sim/cockpit2/radios/indicators/gps_bearing_deg_mag",
    "gps_relative_bearing_deg": "sim/cockpit2/radios/indicators/gps_relative_bearing_deg",
    "gps_distance_nm": "sim/cockpit2/radios/indicators/gps_dme_distance_nm",
    "gps_nav_id": "sim/cockpit2/radios/indicators/gps_nav_id",
    "gps_dme_id": "sim/cockpit2/radios/indicators/gps_dme_id",
    "gps_course_deg": "sim/cockpit/radios/gps_course_degtm",
    "gps_destination_type": "sim/cockpit/gps/destination_type",
    "gps_destination_index": "sim/cockpit/gps/destination_index",
}


def _http_json(url: str, timeout: float = 1.5) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _data_value(payload: Any, default: Any = None) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return default


def _first_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, list):
        value = value[0] if value else default
    try:
        return float(value)
    except Exception:
        return default


def _clean_xplane_string(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("data", "")
    if value is None:
        return ""
    text = str(value).strip().strip("\x00").strip()
    # X-Plane can return fixed-length garbage/placeholder strings like AAAAAA...
    if len(text) > 24 and len(set(text)) <= 2:
        return ""
    if len(text) > 16:
        text = text[:16].strip()
    return text


def _nm_offset(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    # Good enough for local display/route stub. Not navigation-grade.
    brg = math.radians(bearing_deg)
    north_nm = math.cos(brg) * distance_nm
    east_nm = math.sin(brg) * distance_nm
    new_lat = lat + north_nm / 60.0
    cos_lat = max(0.0001, abs(math.cos(math.radians(lat))))
    new_lon = lon + east_nm / (60.0 * cos_lat)
    return new_lat, new_lon


def _find_latest_fms_file() -> Path | None:
    candidates: list[Path] = []
    home = Path.home()
    roots = [
        Path("data/xplane_route"),
        home / "X-Plane 12" / "Output" / "FMS plans",
        home / "Games" / "X-Plane 12" / "Output" / "FMS plans",
        home / ".steam" / "steam" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
        home / ".local" / "share" / "Steam" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
    ]
    for root in roots:
        try:
            if root.exists():
                candidates.extend(root.glob("*.fms"))
        except Exception:
            pass
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_fms_file(path: Path) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception:
        return []

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 4:
            continue
        try:
            lat = float(parts[-2])
            lon = float(parts[-1])
        except Exception:
            continue
        # Airport/waypoint name is usually second token for XP11/XP12 FMS lines.
        ident = parts[1] if len(parts) >= 2 else f"WP{len(points) + 1}"
        if ident.upper() in {"ADEP", "ADES", "APP", "DEP", "DES"} and len(parts) >= 3:
            ident = parts[2]
        points.append({"id": ident, "lat": lat, "lon": lon, "source": "XPLANE_FMS_FILE"})
    return points


class XPlaneWebSource:
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._datarefs_by_name: dict[str, dict[str, Any]] = {}
        self.last_error = ""
        self.last_ok_time = 0.0
        self.last_route_file: str | None = None
        self._last_route_points: list[dict[str, Any]] = []

    def online(self) -> bool:
        try:
            self._ensure_datarefs()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def _ensure_datarefs(self) -> None:
        if self._datarefs_by_name:
            return
        payload = _http_json(f"{self.base_url}/datarefs", timeout=2.0)
        data = payload.get("data", []) if isinstance(payload, dict) else payload
        if not isinstance(data, list):
            raise RuntimeError("Unexpected X-Plane datarefs response")
        self._datarefs_by_name = {
            str(item.get("name")): item
            for item in data
            if isinstance(item, dict) and item.get("name") is not None
        }

    def _value(self, key: str, default: Any = None) -> Any:
        self._ensure_datarefs()
        name = DATAREFS[key]
        ref = self._datarefs_by_name.get(name)
        if not ref:
            return default
        ref_id = ref.get("id")
        payload = _http_json(f"{self.base_url}/datarefs/{ref_id}/value", timeout=1.0)
        return _data_value(payload, default)

    def _num(self, key: str, default: float = 0.0) -> float:
        return _first_number(self._value(key, default), default)

    def _text(self, key: str) -> str:
        return _clean_xplane_string(self._value(key, ""))

    def _route_points(self, lat: float, lon: float, next_wp: str, bearing_deg: float | None, distance_nm: float | None) -> tuple[list[dict[str, Any]], str]:
        fms = _find_latest_fms_file()
        if fms:
            points = parse_fms_file(fms)
            if points:
                self.last_route_file = str(fms)
                self._last_route_points = points
                return points, f"FMS_FILE:{fms.name}"

        points = [{"id": "XPLN", "lat": lat, "lon": lon, "source": "XPLANE_LIVE_POSITION"}]
        if bearing_deg is not None and distance_nm is not None and distance_nm > 0.05:
            dest_lat, dest_lon = _nm_offset(lat, lon, bearing_deg, min(distance_nm, 500.0))
            points.append({"id": next_wp or "GPS", "lat": dest_lat, "lon": dest_lon, "source": "XPLANE_GPS_BEARING_DISTANCE"})
        return points, "XPLANE_ACTIVE_GPS_ONLY"

    def next_truth(self) -> AircraftTruth | None:
        try:
            lat = self._num("lat")
            lon = self._num("lon")
            altitude_ft = self._num("elevation_m") * M_TO_FT
            agl_ft = self._num("agl_m") * M_TO_FT
            ias_kts = self._num("ias_kts")
            tas_kts = self._num("tas_mps") * MPS_TO_KTS
            gs_kts = self._num("gs_mps") * MPS_TO_KTS
            heading = self._num("heading_deg") % 360.0
            pitch = self._num("pitch_deg")
            roll = self._num("roll_deg")
            vs_fpm = self._num("vs_fpm")
            fuel_lbs = self._num("fuel_kg") * KG_TO_LB
            rpm = self._num("engine_rpm")
            egt = self._num("engine_egt_c")
            itt = self._num("engine_itt_c")
            gps_bearing = self._num("gps_bearing_deg", float("nan"))
            gps_distance = self._num("gps_distance_nm", float("nan"))
            gps_course = self._num("gps_course_deg", float("nan"))

            nav_id = self._text("gps_dme_id") or self._text("gps_nav_id")
            if not nav_id:
                nav_id = "GPS"

            bearing_value = gps_bearing if math.isfinite(gps_bearing) else None
            dist_value = gps_distance if math.isfinite(gps_distance) else None
            desired_track = gps_course if math.isfinite(gps_course) else bearing_value
            route_points, route_source = self._route_points(lat, lon, nav_id, bearing_value, dist_value)

            route_name = "XPLANE"
            if len(route_points) >= 2:
                route_name = f"{route_points[0].get('id', 'XPLN')}-{route_points[-1].get('id', nav_id)}"

            self.last_ok_time = time()
            self.last_error = ""
            return AircraftTruth(
                source="XPLANE_WEB_API",
                timestamp=time(),
                route=route_name,
                current_wp=str(route_points[0].get("id", "XPLN")) if route_points else "XPLN",
                next_wp=nav_id,
                route_points=route_points,
                route_source=route_source,
                desired_track_deg=desired_track,
                gps_bearing_deg=bearing_value,
                gps_distance_nm=dist_value,
                gps_nav_id=nav_id,
                lat=lat,
                lon=lon,
                altitude_ft=altitude_ft,
                agl_ft=agl_ft,
                airspeed_kts=ias_kts,
                true_airspeed_kts=tas_kts,
                ground_speed_kts=gs_kts,
                heading_deg=heading,
                vertical_speed_fpm=vs_fpm,
                pitch_deg=pitch,
                roll_deg=roll,
                yaw_deg=heading,
                fuel_lbs=fuel_lbs,
                engine_temp_c=egt or itt or 0.0,
                engine_rpm=rpm,
                engine_egt_c=egt,
                engine_itt_c=itt,
                oat_c=12.0,
                valid=True,
            )
        except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
            self.last_error = str(exc)
            return None
        except Exception as exc:
            self.last_error = f"Unexpected X-Plane source error: {exc}"
            return None

    def status(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "online": self.online(),
            "dataref_count": len(self._datarefs_by_name),
            "last_ok_age_sec": round(time() - self.last_ok_time, 2) if self.last_ok_time else None,
            "last_error": self.last_error,
            "last_route_file": self.last_route_file,
        }
