from __future__ import annotations

from time import time
from typing import Any

from .aircraft_truth import AircraftTruth


def _label(
    *,
    label_octal: str,
    name: str,
    value: float | str | bool | None,
    units: str = "",
    ssm: str = "NORMAL",
    source: str,
    note: str = "educational ARINC-429-style label, not binary encoded",
) -> dict[str, Any]:
    return {
        "schema": "MBIL-ARINC429-LABEL-1",
        "timestamp": time(),
        "bus": "ARINC429_RX_1",
        "label_octal": label_octal,
        "name": name,
        "value": value,
        "units": units,
        "ssm": ssm,
        "source": source,
        "note": note,
    }


def encode_arinc429_labels(truth: AircraftTruth, tick: int) -> list[dict[str, Any]]:
    """Convert adapter aircraft truth into ARINC-429-style labels.

    This is not real 32-bit ARINC word packing yet. It is a lab-friendly
    intermediate format so MBIL can learn and monitor ARINC-style one-way labels
    alongside 1553 messages.
    """

    source = truth.source
    valid_ssm = "NORMAL" if truth.valid else "FAILURE_WARNING"
    gs = truth.ground_speed_kts if truth.ground_speed_kts is not None else truth.airspeed_kts
    tas = truth.true_airspeed_kts if truth.true_airspeed_kts is not None else truth.airspeed_kts

    labels = [
        _label(label_octal="203", name="BARO_ALTITUDE", value=round(truth.altitude_ft, 1), units="ft", ssm=valid_ssm, source=source),
        _label(label_octal="206", name="INDICATED_AIRSPEED", value=round(truth.airspeed_kts, 1), units="kt", ssm=valid_ssm, source=source),
        _label(label_octal="210", name="TRUE_AIRSPEED", value=round(tas, 1), units="kt", ssm=valid_ssm, source=source),
        _label(label_octal="312", name="GROUND_SPEED", value=round(gs, 1), units="kt", ssm=valid_ssm, source=source),
        _label(label_octal="320", name="MAG_HEADING", value=round(truth.heading_deg % 360.0, 2), units="deg", ssm=valid_ssm, source=source),
        _label(label_octal="325", name="PITCH", value=round(truth.pitch_deg, 2), units="deg", ssm=valid_ssm, source=source),
        _label(label_octal="326", name="ROLL", value=round(truth.roll_deg, 2), units="deg", ssm=valid_ssm, source=source),
        _label(label_octal="365", name="VERTICAL_SPEED", value=round(truth.vertical_speed_fpm, 1), units="fpm", ssm=valid_ssm, source=source),
        _label(label_octal="110", name="PRESENT_POSITION_LAT", value=round(truth.lat, 7), units="deg", ssm=valid_ssm, source=source),
        _label(label_octal="111", name="PRESENT_POSITION_LON", value=round(truth.lon, 7), units="deg", ssm=valid_ssm, source=source),
    ]

    if truth.gps_bearing_deg is not None:
        labels.append(_label(label_octal="314", name="GPS_BEARING", value=round(truth.gps_bearing_deg % 360.0, 2), units="deg", ssm=valid_ssm, source=source))
    if truth.gps_distance_nm is not None:
        labels.append(_label(label_octal="351", name="GPS_DISTANCE", value=round(truth.gps_distance_nm, 2), units="nm", ssm=valid_ssm, source=source))
    if truth.engine_rpm is not None:
        labels.append(_label(label_octal="270", name="ENGINE_RPM", value=round(truth.engine_rpm, 1), units="rpm", ssm=valid_ssm, source=source))
    if truth.engine_egt_c is not None:
        labels.append(_label(label_octal="271", name="ENGINE_EGT", value=round(truth.engine_egt_c, 1), units="deg C", ssm=valid_ssm, source=source))
    if truth.fuel_lbs is not None:
        labels.append(_label(label_octal="250", name="FUEL_TOTAL", value=round(truth.fuel_lbs, 1), units="lb", ssm=valid_ssm, source=source))

    for label in labels:
        label["tick"] = tick

    return labels
