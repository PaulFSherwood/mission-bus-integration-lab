from __future__ import annotations

import json
import os
from pathlib import Path
from time import time
from typing import Any

EXCHANGE_DIR = Path("data/exchange")


def ensure_exchange_dirs() -> None:
    EXCHANGE_DIR.mkdir(parents=True, exist_ok=True)
    Path("data/dis_captures").mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: Any) -> None:
    ensure_exchange_dirs()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    os.replace(tmp, path)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_exchange_dirs()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def write_adapter_status(status: dict[str, Any]) -> None:
    status = dict(status)
    status.setdefault("schema", "MBIL-ADAPTER-STATUS-1")
    status.setdefault("timestamp", time())
    atomic_write_json(EXCHANGE_DIR / "adapter_status.json", status)


def write_stub_input_files() -> None:
    atomic_write_json(EXCHANGE_DIR / "arinc429_latest.json", {
        "schema": "MBIL-ARINC429-LATEST-1",
        "stub": True,
        "labels": [],
        "note": "Stub only. Add ARINC 429 labels later.",
    })
    atomic_write_json(EXCHANGE_DIR / "discretes_latest.json", {
        "schema": "MBIL-DISCRETES-LATEST-1",
        "stub": True,
        "signals": {
            "weight_on_wheels": False,
            "gear_down": False,
            "master_caution": False,
        },
    })
    atomic_write_json(EXCHANGE_DIR / "analog_latest.json", {
        "schema": "MBIL-ANALOG-LATEST-1",
        "stub": True,
        "channels": {
            "aoa_vdc": None,
            "trim_position_vdc": None,
            "fuel_quantity_vdc": None,
        },
    })
    atomic_write_json(EXCHANGE_DIR / "ethernet_latest.json", {
        "schema": "MBIL-ETHERNET-LATEST-1",
        "stub": True,
        "packets": [],
        "note": "Reserved for AFDX/ethernet-style avionics data later.",
    })


def write_1553_exchange(messages: list[dict[str, Any]], source_status: dict[str, Any]) -> None:
    ensure_exchange_dirs()

    bus_a = [m for m in messages if m.get("bus") == "BUS_A"]
    bus_b = [m for m in messages if m.get("bus") == "BUS_B"]

    atomic_write_json(EXCHANGE_DIR / "bus1553_A_latest.json", {
        "schema": "MBIL-1553-LATEST-1",
        "timestamp": time(),
        "bus": "BUS_A",
        "messages": bus_a,
    })
    atomic_write_json(EXCHANGE_DIR / "bus1553_B_latest.json", {
        "schema": "MBIL-1553-LATEST-1",
        "timestamp": time(),
        "bus": "BUS_B",
        "messages": bus_b,
    })

    for message in messages:
        append_jsonl(EXCHANGE_DIR / "bus1553_messages.jsonl", message)

    write_stub_input_files()
    write_adapter_status(source_status)
