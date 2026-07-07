from __future__ import annotations

from dataclasses import dataclass, asdict, field
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

    # Route/navigation truth
    route: str = "KPNS-KABQ"
    current_wp: str = "KPNS"
    next_wp: str = "LOXLY"
    route_points: list[dict[str, Any]] = field(default_factory=list)
    route_source: str = "STATIC_ROUTE"
    desired_track_deg: float | None = None
    gps_bearing_deg: float | None = None
    gps_distance_nm: float | None = None
    gps_nav_id: str = ""

    # Aircraft kinematics
    lat: float = 30.47667
    lon: float = -87.18450
    altitude_ft: float = 9600.0
    agl_ft: float | None = None
    airspeed_kts: float = 210.0
    true_airspeed_kts: float | None = None
    ground_speed_kts: float | None = None
    heading_deg: float = 270.0
    vertical_speed_fpm: float = 0.0
    pitch_deg: float = 1.5
    roll_deg: float = 0.0
    yaw_deg: float = 0.0

    # Autopilot / flight director / selected bugs
    ap_engaged: bool = False
    fd_engaged: bool = False
    yd_engaged: bool = False
    ap_hdg_mode: bool = False
    ap_nav_mode: bool = False
    ap_alt_hold: bool = False
    ap_vs_mode: bool = False
    ap_flc_mode: bool = False
    ap_apr_mode: bool = False
    ap_gs_mode: bool = False
    selected_heading_deg: float | None = None
    selected_altitude_ft: float | None = None
    selected_airspeed_kts: float | None = None
    selected_vertical_speed_fpm: float | None = None

    # Engine/fuel/environment
    fuel_lbs: float = 5320.0
    engine_temp_c: float = 625.0
    engine_rpm: float | None = None
    engine_egt_c: float | None = None
    engine_itt_c: float | None = None
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

        def opt_num(name: str) -> float | None:
            value = data.get(name)
            if value is None:
                return None
            try:
                return float(value)
            except Exception:
                return None

        def text(name: str, default: str) -> str:
            value = data.get(name, default)
            if value is None:
                return default
            return str(value)

        route_points = data.get("route_points", [])
        if not isinstance(route_points, list):
            route_points = []

        return cls(
            source=text("source", source),
            timestamp=num("timestamp", time()),
            route=text("route", cls.route),
            current_wp=text("current_wp", data.get("from_wp", cls.current_wp)),
            next_wp=text("next_wp", data.get("to_wp", cls.next_wp)),
            route_points=route_points,
            route_source=text("route_source", "MAPPING"),
            desired_track_deg=opt_num("desired_track_deg"),
            gps_bearing_deg=opt_num("gps_bearing_deg"),
            gps_distance_nm=opt_num("gps_distance_nm"),
            gps_nav_id=text("gps_nav_id", ""),
            lat=num("lat", cls.lat),
            lon=num("lon", cls.lon),
            altitude_ft=num("altitude_ft", data.get("altitude", cls.altitude_ft)),
            agl_ft=opt_num("agl_ft"),
            airspeed_kts=num("airspeed_kts", data.get("airspeed", cls.airspeed_kts)),
            true_airspeed_kts=opt_num("true_airspeed_kts"),
            ground_speed_kts=opt_num("ground_speed_kts"),
            heading_deg=num("heading_deg", data.get("heading", cls.heading_deg)),
            vertical_speed_fpm=num("vertical_speed_fpm", data.get("vs_fpm", cls.vertical_speed_fpm)),
            pitch_deg=num("pitch_deg", cls.pitch_deg),
            roll_deg=num("roll_deg", cls.roll_deg),
            yaw_deg=num("yaw_deg", data.get("heading_deg", cls.yaw_deg)),
            ap_engaged=bool(data.get("ap_engaged", False)),
            fd_engaged=bool(data.get("fd_engaged", False)),
            yd_engaged=bool(data.get("yd_engaged", False)),
            ap_hdg_mode=bool(data.get("ap_hdg_mode", False)),
            ap_nav_mode=bool(data.get("ap_nav_mode", False)),
            ap_alt_hold=bool(data.get("ap_alt_hold", False)),
            ap_vs_mode=bool(data.get("ap_vs_mode", False)),
            ap_flc_mode=bool(data.get("ap_flc_mode", False)),
            ap_apr_mode=bool(data.get("ap_apr_mode", False)),
            ap_gs_mode=bool(data.get("ap_gs_mode", False)),
            selected_heading_deg=opt_num("selected_heading_deg"),
            selected_altitude_ft=opt_num("selected_altitude_ft"),
            selected_airspeed_kts=opt_num("selected_airspeed_kts"),
            selected_vertical_speed_fpm=opt_num("selected_vertical_speed_fpm"),
            fuel_lbs=num("fuel_lbs", cls.fuel_lbs),
            engine_temp_c=num("engine_temp_c", cls.engine_temp_c),
            engine_rpm=opt_num("engine_rpm"),
            engine_egt_c=opt_num("engine_egt_c"),
            engine_itt_c=opt_num("engine_itt_c"),
            oat_c=num("oat_c", cls.oat_c),
            valid=bool(data.get("valid", True)),
        )
