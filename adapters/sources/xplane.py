from __future__ import annotations

import base64
import json
import math
import os
import re
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

IDENT_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,7}$")
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]{4,}$")


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

    # Autopilot / flight-director. Missing datarefs are treated as OFF/unknown.
    "ap_state": "sim/cockpit/autopilot/autopilot_state",
    "ap_on": "sim/cockpit2/autopilot/autopilot_on",
    "fd_mode": "sim/cockpit2/autopilot/flight_director_mode",
    "yd_on": "sim/cockpit2/autopilot/yaw_damper_on",
    "hdg_status": "sim/cockpit2/autopilot/heading_status",
    "nav_status": "sim/cockpit2/autopilot/nav_status",
    "alt_status": "sim/cockpit2/autopilot/altitude_hold_status",
    "vs_status": "sim/cockpit2/autopilot/vvi_status",
    "spd_status": "sim/cockpit2/autopilot/speed_status",
    "apr_status": "sim/cockpit2/autopilot/approach_status",
    "gs_status": "sim/cockpit2/autopilot/glideslope_status",
    "gpss_status": "sim/cockpit2/autopilot/gpss_status",
    "fms_vnav": "sim/cockpit2/autopilot/fms_vnav",
    "selected_heading_deg": "sim/cockpit2/autopilot/heading_dial_deg_mag_pilot",
    "selected_altitude_ft": "sim/cockpit2/autopilot/altitude_dial_ft",
    "selected_airspeed": "sim/cockpit2/autopilot/airspeed_dial_kts_mach",
    "selected_vs_fpm": "sim/cockpit2/autopilot/vvi_dial_fpm",
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


def _valid_ident(text: str) -> bool:
    return bool(IDENT_RE.match(text or ""))


def _clean_identifier_text(text: str) -> str:
    text = (text or "").split("\x00", 1)[0].strip().upper()
    text = "".join(ch for ch in text if ch.isalnum() or ch in {"_", "-"})
    if len(text) > 8:
        return ""
    if len(text) >= 4 and len(set(text)) <= 1:
        return ""
    return text if _valid_ident(text) else ""


def _decode_xplane_fixed_string(text: str) -> str:
    # Some X-Plane string datarefs arrive through the Web API as base64-ish
    # fixed buffers. Example: TE9YTFkAAAAAAAA -> LOXLY + NUL padding.
    raw = (text or "").strip()
    if not raw or not BASE64_RE.match(raw):
        return ""
    try:
        padded = raw + ("=" * ((4 - len(raw) % 4) % 4))
        decoded = base64.b64decode(padded, validate=False)
        return decoded.decode("ascii", errors="ignore")
    except Exception:
        return ""


def _clean_xplane_string(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("data", "")
    if value is None:
        return ""

    raw = str(value).strip()

    direct = _clean_identifier_text(raw)
    if direct:
        return direct

    decoded = _clean_identifier_text(_decode_xplane_fixed_string(raw))
    if decoded:
        return decoded

    # Last chance: fixed buffers sometimes look like IDENT + NULs, spaces, or filler.
    no_nuls = raw.split("\x00", 1)[0].strip()
    direct = _clean_identifier_text(no_nuls)
    return direct


def _distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    avg_lat = math.radians((lat1 + lat2) / 2.0)
    north_nm = (lat2 - lat1) * 60.0
    east_nm = (lon2 - lon1) * 60.0 * math.cos(avg_lat)
    return math.sqrt(north_nm * north_nm + east_nm * east_nm)


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = math.pi / 180.0
    p1 = lat1 * r
    p2 = lat2 * r
    dlon = (lon2 - lon1) * r
    y = math.sin(dlon) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _point_ident(point: dict[str, Any], fallback: str = "WP") -> str:
    return _clean_xplane_string(point.get("id") or point.get("ident") or point.get("name") or fallback) or fallback


def _route_index_by_ident(points: list[dict[str, Any]], ident: str) -> int:
    ident = _clean_xplane_string(ident)
    if not ident:
        return -1
    for index, point in enumerate(points):
        if _point_ident(point).upper() == ident.upper():
            return index
    return -1


def _active_leg_from_route(points: list[dict[str, Any]], lat: float, lon: float, live_next_wp: str = "") -> tuple[str, str]:
    if len(points) < 2:
        only = _point_ident(points[0], "XPLN") if points else "XPLN"
        return only, live_next_wp or "GPS"

    live_index = _route_index_by_ident(points, live_next_wp)
    if live_index > 0:
        return _point_ident(points[live_index - 1]), _point_ident(points[live_index])
    if live_index == 0:
        return _point_ident(points[0]), _point_ident(points[1])

    nearest = min(range(len(points)), key=lambda i: _distance_nm(lat, lon, float(points[i].get("lat", lat)), float(points[i].get("lon", lon))))
    if nearest >= len(points) - 1:
        return _point_ident(points[-2]), _point_ident(points[-1])
    return _point_ident(points[nearest]), _point_ident(points[nearest + 1])


def _route_point(points: list[dict[str, Any]], ident: str) -> dict[str, Any] | None:
    index = _route_index_by_ident(points, ident)
    if index >= 0:
        return points[index]
    return None


def _nm_offset(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    # Good enough for local display/route stub. Not navigation-grade.
    brg = math.radians(bearing_deg)
    north_nm = math.cos(brg) * distance_nm
    east_nm = math.sin(brg) * distance_nm
    new_lat = lat + north_nm / 60.0
    cos_lat = max(0.0001, abs(math.cos(math.radians(lat))))
    new_lon = lon + east_nm / (60.0 * cos_lat)
    return new_lat, new_lon


def _fms_search_roots() -> list[Path]:
    home = Path.home()
    roots: list[Path] = []

    env_file = os.environ.get("MBIL_XPLANE_FMS_FILE")
    if env_file:
        roots.append(Path(env_file))

    env_dir = os.environ.get("MBIL_XPLANE_FMS_DIR") or os.environ.get("XPLANE_FMS_PLANS_DIR")
    if env_dir:
        roots.append(Path(env_dir))

    roots.extend([
        Path("data/xplane_route"),
        home / "X-Plane 12" / "Output" / "FMS plans",
        home / "Documents" / "X-Plane 12" / "Output" / "FMS plans",
        home / "Games" / "X-Plane 12" / "Output" / "FMS plans",
        home / ".steam" / "steam" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
        home / ".steam" / "debian-installation" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
        home / ".local" / "share" / "Steam" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
        home / "snap" / "steam" / "common" / ".local" / "share" / "Steam" / "steamapps" / "common" / "X-Plane 12" / "Output" / "FMS plans",
    ])
    return roots


def _find_latest_fms_file() -> Path | None:
    candidates: list[Path] = []
    for root in _fms_search_roots():
        try:
            if root.is_file() and root.suffix.lower() == ".fms":
                candidates.append(root)
            elif root.exists():
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
        ident = _clean_xplane_string(ident) or f"WP{len(points) + 1}"
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

    def _mode_on(self, key: str) -> bool:
        return self._num(key, 0.0) > 0.5

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

            ap_state = self._num("ap_state", 0.0)
            ap_on = self._mode_on("ap_on") or ap_state > 0.5
            fd_on = self._mode_on("fd_mode") or ap_on
            yd_on = self._mode_on("yd_on")
            hdg_mode = self._mode_on("hdg_status")
            nav_mode = self._mode_on("nav_status") or self._mode_on("gpss_status")
            alt_hold = self._mode_on("alt_status")
            vs_mode = self._mode_on("vs_status")
            flc_mode = self._mode_on("spd_status")
            apr_mode = self._mode_on("apr_status")
            gs_mode = self._mode_on("gs_status") or self._mode_on("fms_vnav")
            selected_heading = self._num("selected_heading_deg", float("nan"))
            selected_altitude = self._num("selected_altitude_ft", float("nan"))
            selected_airspeed = self._num("selected_airspeed", float("nan"))
            selected_vs = self._num("selected_vs_fpm", float("nan"))

            live_nav_id = self._text("gps_dme_id") or self._text("gps_nav_id")

            bearing_value = gps_bearing if math.isfinite(gps_bearing) and gps_bearing >= 0.0 else None
            dist_value = gps_distance if math.isfinite(gps_distance) and gps_distance > 0.05 else None
            route_points, route_source = self._route_points(lat, lon, live_nav_id, bearing_value, dist_value)

            current_wp, next_wp = _active_leg_from_route(route_points, lat, lon, live_nav_id)
            next_point = _route_point(route_points, next_wp)
            current_point = _route_point(route_points, current_wp)

            if next_point is not None:
                bearing_value = _bearing_deg(lat, lon, float(next_point.get("lat", lat)), float(next_point.get("lon", lon)))
                if dist_value is None or route_source.startswith("FMS_FILE"):
                    dist_value = _distance_nm(lat, lon, float(next_point.get("lat", lat)), float(next_point.get("lon", lon)))

            if current_point is not None and next_point is not None:
                desired_track = _bearing_deg(
                    float(current_point.get("lat", lat)),
                    float(current_point.get("lon", lon)),
                    float(next_point.get("lat", lat)),
                    float(next_point.get("lon", lon)),
                )
            else:
                desired_track = gps_course if math.isfinite(gps_course) else bearing_value

            nav_id = live_nav_id or next_wp or "GPS"

            route_name = "XPLANE"
            if len(route_points) >= 2:
                route_name = f"{_point_ident(route_points[0], 'XPLN')}-{_point_ident(route_points[-1], nav_id)}"

            self.last_ok_time = time()
            self.last_error = ""
            return AircraftTruth(
                source="XPLANE_WEB_API",
                timestamp=time(),
                route=route_name,
                current_wp=current_wp,
                next_wp=next_wp,
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
                ap_engaged=ap_on,
                fd_engaged=fd_on,
                yd_engaged=yd_on,
                ap_hdg_mode=hdg_mode,
                ap_nav_mode=nav_mode,
                ap_alt_hold=alt_hold,
                ap_vs_mode=vs_mode,
                ap_flc_mode=flc_mode,
                ap_apr_mode=apr_mode,
                ap_gs_mode=gs_mode,
                selected_heading_deg=selected_heading if math.isfinite(selected_heading) else None,
                selected_altitude_ft=selected_altitude if math.isfinite(selected_altitude) else None,
                selected_airspeed_kts=selected_airspeed if math.isfinite(selected_airspeed) else None,
                selected_vertical_speed_fpm=selected_vs if math.isfinite(selected_vs) else None,
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
            "fms_search_roots": [str(root) for root in _fms_search_roots()],
        }
