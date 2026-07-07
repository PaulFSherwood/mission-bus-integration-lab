from __future__ import annotations

import copy
import json
from pathlib import Path
from time import time
from typing import Any

EXCHANGE_DIR = Path("data/exchange")


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text())
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Could not read {path}: {exc}",
        }


def _file_age_sec(path: Path) -> float | None:
    try:
        if not path.exists():
            return None
        return max(0.0, time() - path.stat().st_mtime)
    except Exception:
        return None


def read_adapter_status() -> dict[str, Any]:
    status = _read_json(
        EXCHANGE_DIR / "adapter_status.json",
        {
            "ok": False,
            "adapter_online": False,
            "active_source": "NONE",
            "message": "No adapter_status.json found. Start an MBIL adapter first.",
        },
    )
    if isinstance(status, dict):
        age = _file_age_sec(EXCHANGE_DIR / "adapter_status.json")
        status["file_age_sec"] = round(age, 3) if age is not None else None
    return status


def read_exchange_latest() -> dict[str, Any]:
    return {
        "adapter_status": read_adapter_status(),
        "bus1553_a": _read_json(EXCHANGE_DIR / "bus1553_A_latest.json", {"messages": []}),
        "bus1553_b": _read_json(EXCHANGE_DIR / "bus1553_B_latest.json", {"messages": []}),
        "arinc429": _read_json(EXCHANGE_DIR / "arinc429_latest.json", {"labels": [], "stub": True}),
        "route": _read_json(EXCHANGE_DIR / "route_latest.json", {"route_points": [], "stub": True}),
        "discretes": _read_json(EXCHANGE_DIR / "discretes_latest.json", {"signals": {}, "stub": True}),
        "analog": _read_json(EXCHANGE_DIR / "analog_latest.json", {"channels": {}, "stub": True}),
        "ethernet": _read_json(EXCHANGE_DIR / "ethernet_latest.json", {"packets": [], "stub": True}),
    }


def read_1553_exchange_messages() -> list[dict[str, Any]]:
    latest = read_exchange_latest()
    messages: list[dict[str, Any]] = []
    for key in ("bus1553_a", "bus1553_b"):
        block = latest.get(key, {})
        if isinstance(block, dict):
            messages.extend(block.get("messages", []) or [])
    messages.sort(key=lambda m: (int(m.get("tick", 0) or 0), float(m.get("timestamp", 0) or 0)))
    return messages


def latest_message_by_type(messages: list[dict[str, Any]], message_type: str) -> dict[str, Any] | None:
    for msg in reversed(messages):
        if msg.get("message_type") == message_type:
            return msg
    return None


def payload_for(messages: list[dict[str, Any]], message_type: str) -> dict[str, Any]:
    msg = latest_message_by_type(messages, message_type)
    if not msg:
        return {}
    payload = msg.get("payload") or {}
    return payload if isinstance(payload, dict) else {}


def exchange_bus_age_sec() -> float | None:
    ages = [
        _file_age_sec(EXCHANGE_DIR / "bus1553_A_latest.json"),
        _file_age_sec(EXCHANGE_DIR / "bus1553_B_latest.json"),
    ]
    ages = [age for age in ages if age is not None]
    if not ages:
        return None
    return min(ages)


def exchange_is_fresh(stale_after_sec: float = 3.0) -> bool:
    status = read_adapter_status()
    bus_age = exchange_bus_age_sec()
    if bus_age is None:
        return False
    return bool(status.get("adapter_online")) and bus_age <= stale_after_sec


def exchange_input_status(stale_after_sec: float = 3.0) -> dict[str, Any]:
    status = read_adapter_status()
    messages = read_1553_exchange_messages()
    bus_age = exchange_bus_age_sec()
    return {
        "schema": "MBIL-INPUT-STATUS-1",
        "adapter": status,
        "exchange_dir": str(EXCHANGE_DIR),
        "bus_age_sec": round(bus_age, 3) if bus_age is not None else None,
        "fresh": exchange_is_fresh(stale_after_sec),
        "stale_after_sec": stale_after_sec,
        "message_count": len(messages),
        "message_types": sorted({str(m.get("message_type")) for m in messages if m.get("message_type")}),
    }


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _fmt_int(value: float, suffix: str = "") -> str:
    return f"{round(value):,}{(' ' + suffix) if suffix else ''}"


def build_api_state_from_exchange(
    fallback_state: dict[str, Any],
    *,
    input_mode: str = "auto",
    stale_after_sec: float = 3.0,
) -> dict[str, Any]:
    """Build /api/state from adapter exchange files when enabled.

    Modes:
    - internal: always use MBIL's built-in simulator state.
    - auto: use exchange files only when adapter data is fresh.
    - exchange: prefer exchange files even if stale/missing, but report stale/missing.
    """

    mode = (input_mode or "auto").lower().strip()
    if mode not in {"internal", "auto", "exchange"}:
        mode = "auto"

    state = copy.deepcopy(fallback_state)
    status = exchange_input_status(stale_after_sec)
    messages = read_1553_exchange_messages()
    fresh = bool(status.get("fresh"))

    state["input"] = {
        "mode": mode,
        "active": "internal",
        "fresh": fresh,
        "adapter_status": status.get("adapter"),
        "bus_age_sec": status.get("bus_age_sec"),
        "message_count": len(messages),
    }

    if mode == "internal":
        return state

    if mode == "auto" and not fresh:
        state["input"]["active"] = "internal_fallback"
        return state

    if not messages:
        state["input"]["active"] = "exchange_missing"
        state.setdefault("sim", {})["state"] = "NO EXCHANGE DATA"
        return state

    air = payload_for(messages, "AIR_DATA")
    nav = payload_for(messages, "NAV_DATA")
    attitude = payload_for(messages, "ATTITUDE_DATA")
    autopilot = payload_for(messages, "AUTOPILOT_DATA")
    engine = payload_for(messages, "ENGINE_DATA")
    fuel = payload_for(messages, "FUEL_DATA")
    taws = payload_for(messages, "TAWS_DATA")
    weather_radar = payload_for(messages, "WEATHER_RADAR")
    latest_exchange = read_exchange_latest()
    route_block = latest_exchange.get("route", {}) if isinstance(latest_exchange.get("route", {}), dict) else {}
    arinc_block = latest_exchange.get("arinc429", {}) if isinstance(latest_exchange.get("arinc429", {}), dict) else {}

    fallback_aircraft = state.get("aircraft", {}) or {}
    fallback_sim = state.get("sim", {}) or {}

    altitude_ft = _num(air.get("altitude_ft"), _num(str(fallback_aircraft.get("altitude", "9600")).replace(",", "").split()[0], 9600))
    airspeed_kts = _num(air.get("airspeed_kts"), _num(str(fallback_aircraft.get("airspeed", "210")).split()[0], 210))
    vertical_speed_fpm = _num(air.get("vertical_speed_fpm"), _num(str(fallback_aircraft.get("vertical_speed", "0")).replace("+", "").split()[0], 0))
    heading_deg = _num(nav.get("heading_deg"), _num(fallback_aircraft.get("heading", 0), 0)) % 360
    lat = _num(nav.get("lat"), _num(fallback_aircraft.get("lat"), 0))
    lon = _num(nav.get("lon"), _num(fallback_aircraft.get("lon"), 0))
    fuel_lbs = _num(fuel.get("fuel_lbs"), _num(str(fallback_aircraft.get("fuel", "5320")).replace(",", "").split()[0], 5320))
    engine_temp_c = _num(engine.get("engine_temp_c"), _num(str(fallback_aircraft.get("engine_temp", "625")).split()[0], 625))
    pitch_deg = _num(attitude.get("pitch_deg"), _num(fallback_aircraft.get("pitch_deg"), 0))
    roll_deg = _num(attitude.get("roll_deg"), _num(fallback_aircraft.get("roll_deg"), 0))

    latest_tick = max(int(m.get("tick", 0) or 0) for m in messages)
    source = str(nav.get("source") or status.get("adapter", {}).get("active_source") or "EXCHANGE")
    route = str(route_block.get("route") or nav.get("route") or fallback_sim.get("route") or "EXTERNAL")
    current_wp = str(route_block.get("current_wp") or nav.get("current_wp") or fallback_sim.get("current_wp") or "EXT")
    next_wp = str(route_block.get("next_wp") or nav.get("next_wp") or fallback_sim.get("next_wp") or "EXT")

    state["input"]["active"] = "exchange" if fresh else "exchange_stale"
    state["input"]["source"] = source

    state["sim"] = {
        **fallback_sim,
        "tick": latest_tick,
        "state": "EXTERNAL INPUT" if fresh else "EXTERNAL STALE",
        "route": route,
        "current_wp": current_wp,
        "next_wp": next_wp,
        "route_source": route_block.get("route_source") or nav.get("route_source"),
        "desired_track_deg": route_block.get("desired_track_deg") or nav.get("desired_track_deg"),
        "gps_bearing_deg": route_block.get("gps_bearing_deg") or nav.get("gps_bearing_deg"),
        "gps_distance_nm": route_block.get("gps_distance_nm") or nav.get("gps_distance_nm"),
        "gps_nav_id": route_block.get("gps_nav_id") or nav.get("gps_nav_id"),
    }

    state["aircraft"] = {
        **fallback_aircraft,
        "altitude": _fmt_int(altitude_ft, "FT"),
        "airspeed": _fmt_int(airspeed_kts, "KTS"),
        "ground_speed": _fmt_int(_num(air.get("ground_speed_kts"), airspeed_kts), "KTS"),
        "true_airspeed": _fmt_int(_num(air.get("true_airspeed_kts"), airspeed_kts), "KTS"),
        "agl": _fmt_int(_num(air.get("agl_ft"), 0), "FT"),
        "heading": f"{round(heading_deg):03d}",
        "vertical_speed": f"{vertical_speed_fpm:+.0f} FPM",
        "fuel": _fmt_int(fuel_lbs, "LBS"),
        "engine_temp": f"{engine_temp_c:.0f} °C",
        "lat": lat,
        "lon": lon,
        "current_wp": current_wp,
        "next_wp": next_wp,
        "pitch_deg": pitch_deg,
        "roll_deg": roll_deg,
        "oat": f"{_num(air.get('oat_c'), 0):.0f} °C",
    }

    state["bus1553"] = {
        **(state.get("bus1553", {}) or {}),
        "active_controller": "MC1",
        "bus_a": "ONLINE" if any(m.get("bus") == "BUS_A" for m in messages) else "NO DATA",
        "bus_b": "ONLINE" if any(m.get("bus") == "BUS_B" for m in messages) else "NO DATA",
        "message_count": len(messages),
        "source": source,
    }


    ap_modes = autopilot.get("modes") if isinstance(autopilot.get("modes"), dict) else {}
    state["autopilot"] = {
        "source": autopilot.get("source", source),
        "ap_engaged": bool(autopilot.get("ap_engaged", False)),
        "fd_engaged": bool(autopilot.get("fd_engaged", False)),
        "yd_engaged": bool(autopilot.get("yd_engaged", False)),
        "modes": {
            "HDG": bool(ap_modes.get("HDG", False)),
            "NAV": bool(ap_modes.get("NAV", False)),
            "ALT": bool(ap_modes.get("ALT", False)),
            "VS": bool(ap_modes.get("VS", False)),
            "FLC": bool(ap_modes.get("FLC", False)),
            "APR": bool(ap_modes.get("APR", False)),
            "GS": bool(ap_modes.get("GS", False)),
        },
        "selected_heading_deg": autopilot.get("selected_heading_deg"),
        "selected_altitude_ft": autopilot.get("selected_altitude_ft"),
        "selected_airspeed_kts": autopilot.get("selected_airspeed_kts"),
        "selected_vertical_speed_fpm": autopilot.get("selected_vertical_speed_fpm"),
        "valid": bool(autopilot) and fresh,
    }

    bus_a_online = state["bus1553"].get("bus_a") == "ONLINE"
    bus_b_online = state["bus1553"].get("bus_b") == "ONLINE"
    state["mission_computers"] = {
        "mc1": {
            "role": "PRIMARY",
            "state": "OK" if fresh and bus_a_online else "STALE",
            "heartbeat": f"00:00:{latest_tick / 10.0:05.2f}",
            "bus_a": state["bus1553"].get("bus_a"),
            "bus_b": state["bus1553"].get("bus_b"),
            "inputs": {
                "air_data": "OK" if air else "NO DATA",
                "nav": "OK" if nav else "NO DATA",
                "engine": "OK" if engine else "NO DATA",
                "fuel": "OK" if fuel else "NO DATA",
            },
            "outputs": {"displays": "OK" if fresh else "STALE", "autopilot": "OK" if autopilot else "NO DATA", "other_mc": "OK" if bus_b_online else "NO DATA"},
        },
        "mc2": {
            "role": "STANDBY",
            "state": "OK" if fresh and bus_b_online else "STALE",
            "heartbeat": f"00:00:{latest_tick / 10.0 + 0.02:05.2f}",
            "bus_a": state["bus1553"].get("bus_a"),
            "bus_b": state["bus1553"].get("bus_b"),
            "inputs": {
                "air_data": "OK" if air else "NO DATA",
                "nav": "OK" if nav else "NO DATA",
                "engine": "OK" if engine else "NO DATA",
                "fuel": "OK" if fuel else "NO DATA",
            },
            "outputs": {"displays": "STANDBY" if fresh else "STALE", "autopilot": "STANDBY", "other_mc": "OK" if bus_a_online else "NO DATA"},
        },
    }

    state["pfd"] = {
        "source": "1553:AIR_DATA+ATTITUDE_DATA+AUTOPILOT_DATA",
        "pitch_deg": pitch_deg,
        "roll_deg": roll_deg,
        "heading_deg": heading_deg,
        "airspeed_kts": airspeed_kts,
        "altitude_ft": altitude_ft,
        "vertical_speed_fpm": vertical_speed_fpm,
        "bearing_pointer_deg": route_block.get("gps_bearing_deg") or nav.get("gps_bearing_deg"),
        "bearing_pointer_source": route_block.get("gps_nav_id") or nav.get("gps_nav_id") or next_wp,
    }

    state["nav_display"] = {
        "source": "1553:NAV_DATA",
        "route": route,
        "current_wp": current_wp,
        "next_wp": next_wp,
        "desired_track_deg": route_block.get("desired_track_deg") or nav.get("desired_track_deg"),
        "gps_bearing_deg": route_block.get("gps_bearing_deg") or nav.get("gps_bearing_deg"),
        "gps_distance_nm": route_block.get("gps_distance_nm") or nav.get("gps_distance_nm"),
        "route_source": route_block.get("route_source") or nav.get("route_source"),
    }

    route_points = route_block.get("route_points") or nav.get("route_points") or []
    if isinstance(route_points, list) and route_points:
        state["route_points"] = route_points
        state["xplane_route"] = {
            "source": route_block.get("source") or nav.get("source"),
            "route_source": route_block.get("route_source") or nav.get("route_source"),
            "route": route,
            "current_wp": current_wp,
            "next_wp": next_wp,
            "point_count": len(route_points),
            "gps_bearing_deg": route_block.get("gps_bearing_deg") or nav.get("gps_bearing_deg"),
            "gps_distance_nm": route_block.get("gps_distance_nm") or nav.get("gps_distance_nm"),
        }

    labels = arinc_block.get("labels", []) if isinstance(arinc_block.get("labels", []), list) else []
    state["arinc429"] = {
        "source": arinc_block.get("source", source),
        "label_count": len(labels),
        "labels": labels[:40],
        "fresh": fresh,
        "stub": bool(arinc_block.get("stub", False)),
    }

    if taws:
        state["taws"] = {
            "source": "1553:TAWS_DATA",
            "mode": taws.get("mode", "SIM_ONLY"),
            "alert_state": taws.get("alert_state", "CLEAR"),
            "range_nm": _num(taws.get("range_nm"), 40),
            "terrain_source": taws.get("terrain_source", "UNKNOWN"),
            "terrain_under_ft": _num(taws.get("terrain_under_ft", taws.get("terrain_under_aircraft_ft")), 0),
            "clearance_ft": _num(taws.get("clearance_ft"), 0),
            "worst_clearance_ft": _num(taws.get("worst_clearance_ft"), 0),
            "worst_terrain_ft": _num(taws.get("worst_terrain_ft"), 0),
            "worst_point": taws.get("worst_point", {}),
            "terrain_return_count": len(taws.get("terrain_returns", [])) if isinstance(taws.get("terrain_returns", []), list) else 0,
            "terrain_returns": taws.get("terrain_returns", []) if isinstance(taws.get("terrain_returns", []), list) else [],
            "valid": bool(taws.get("valid", True)),
        }

    if weather_radar:
        state["weather_radar"] = {
            "source": "1553:WEATHER_RADAR",
            "mode": weather_radar.get("mode", "SIM_ONLY"),
            "range_nm": _num(weather_radar.get("range_nm"), 40),
            "motion": weather_radar.get("motion", "LOCAL_SIM"),
            "cells": weather_radar.get("cells", []) if isinstance(weather_radar.get("cells", []), list) else [],
            "cell_count": int(_num(weather_radar.get("cell_count"), 0)),
            "severe_count": int(_num(weather_radar.get("severe_count"), 0)),
            "lightning_count": int(_num(weather_radar.get("lightning_count"), 0)),
            "valid": bool(weather_radar.get("valid", True)),
        }

    state["radar_display"] = {
        "source": state.get("weather_radar", {}).get("source", "1553:WEATHER_RADAR" if weather_radar else "NO DATA"),
        "range_nm": state.get("weather_radar", {}).get("range_nm", 40),
        "next_wp": next_wp,
        "gps_bearing_deg": route_block.get("gps_bearing_deg") or nav.get("gps_bearing_deg"),
        "gps_distance_nm": route_block.get("gps_distance_nm") or nav.get("gps_distance_nm"),
    }

    return state


def messages_for_api(
    fallback_messages: list[dict[str, Any]],
    *,
    input_mode: str = "auto",
    stale_after_sec: float = 3.0,
) -> dict[str, Any]:
    mode = (input_mode or "auto").lower().strip()
    messages = read_1553_exchange_messages()
    fresh = exchange_is_fresh(stale_after_sec)

    if mode == "internal":
        return {"source": "internal", "fresh": True, "messages": fallback_messages}

    if mode == "exchange":
        return {"source": "exchange" if messages else "exchange_missing", "fresh": fresh, "messages": list(reversed(messages))}

    if fresh and messages:
        return {"source": "exchange", "fresh": True, "messages": list(reversed(messages))}

    return {"source": "internal_fallback", "fresh": fresh, "messages": fallback_messages}
