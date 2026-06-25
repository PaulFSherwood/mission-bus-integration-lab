from __future__ import annotations

from time import time
from typing import Any

from .aircraft_truth import AircraftTruth
from .terrain_model import taws_payload_for
from .weather_model import weather_radar_payload_for


def _message(
    *,
    tick: int,
    bus: str,
    controller: str,
    rt: str,
    rt_address: int,
    subaddress: int,
    message_type: str,
    payload: dict[str, Any],
    word_count: int = 8,
    direction: str = "RT_TO_BC",
    status: str = "OK",
) -> dict[str, Any]:
    return {
        "schema": "MBIL-1553-MESSAGE-1",
        "tick": tick,
        "timestamp": time(),
        "bus": bus,
        "controller": controller,
        "rt": rt,
        "rt_address": rt_address,
        "subaddress": subaddress,
        "direction": direction,
        "word_count": word_count,
        "message_type": message_type,
        "status": status,
        "payload": payload,
    }


def encode_1553_messages(truth: AircraftTruth, tick: int) -> list[dict[str, Any]]:
    """Convert adapter-side aircraft truth into 1553-like RT messages.

    This is intentionally not real binary 1553. It is an educational exchange
    format that keeps the same BC/RT/subaddress/message idea.
    """

    source_status = "OK" if truth.valid else "STALE"

    bus_a_air_data = _message(
        tick=tick,
        bus="BUS_A",
        controller="MC1",
        rt="AIR_DATA_RT",
        rt_address=1,
        subaddress=1,
        message_type="AIR_DATA",
        status=source_status,
        payload={
            "altitude_ft": round(truth.altitude_ft, 1),
            "airspeed_kts": round(truth.airspeed_kts, 1),
            "vertical_speed_fpm": round(truth.vertical_speed_fpm, 1),
            "oat_c": round(truth.oat_c, 1),
        },
    )

    return [
        bus_a_air_data,
        _message(
            tick=tick,
            bus="BUS_A",
            controller="MC1",
            rt="NAV_RT",
            rt_address=2,
            subaddress=1,
            message_type="NAV_DATA",
            status=source_status,
            payload={
                "lat": truth.lat,
                "lon": truth.lon,
                "heading_deg": round(truth.heading_deg % 360.0, 1),
                "route": truth.route,
                "current_wp": truth.current_wp,
                "next_wp": truth.next_wp,
                "source": truth.source,
            },
        ),
        _message(
            tick=tick,
            bus="BUS_A",
            controller="MC1",
            rt="ATTITUDE_RT",
            rt_address=6,
            subaddress=1,
            message_type="ATTITUDE_DATA",
            status=source_status,
            payload={
                "pitch_deg": round(truth.pitch_deg, 2),
                "roll_deg": round(truth.roll_deg, 2),
                "yaw_deg": round(truth.yaw_deg, 2),
            },
        ),
        _message(
            tick=tick,
            bus="BUS_A",
            controller="MC1",
            rt="ENGINE_RT",
            rt_address=3,
            subaddress=1,
            message_type="ENGINE_DATA",
            status=source_status,
            payload={
                "engine_temp_c": round(truth.engine_temp_c, 1),
                "engine_status": "NORMAL" if truth.engine_temp_c < 760 else "HOT",
            },
        ),
        _message(
            tick=tick,
            bus="BUS_A",
            controller="MC1",
            rt="FUEL_RT",
            rt_address=4,
            subaddress=1,
            message_type="FUEL_DATA",
            status=source_status,
            payload={
                "fuel_lbs": round(truth.fuel_lbs, 1),
                "fuel_status": "NORMAL" if truth.fuel_lbs > 900 else "LOW",
            },
        ),
        _message(
            tick=tick,
            bus="BUS_A",
            controller="MC1",
            rt="TERRAIN_RT",
            rt_address=7,
            subaddress=1,
            message_type="TAWS_DATA",
            status=source_status,
            word_count=16,
            payload=taws_payload_for(truth),
        ),
        _message(
            tick=tick,
            bus="BUS_A",
            controller="MC1",
            rt="WEATHER_RADAR_RT",
            rt_address=5,
            subaddress=1,
            message_type="WEATHER_RADAR",
            status=source_status,
            word_count=20,
            payload=weather_radar_payload_for(truth),
        ),
        _message(
            tick=tick,
            bus="BUS_B",
            controller="MC2",
            rt="AIR_DATA_RT",
            rt_address=1,
            subaddress=1,
            message_type="AIR_DATA",
            status=source_status,
            payload=bus_a_air_data["payload"],
        ),
        _message(
            tick=tick,
            bus="BUS_B",
            controller="MC2",
            rt="TERRAIN_RT",
            rt_address=7,
            subaddress=1,
            message_type="TAWS_DATA",
            status=source_status,
            word_count=16,
            payload=taws_payload_for(truth),
        ),
    ]
