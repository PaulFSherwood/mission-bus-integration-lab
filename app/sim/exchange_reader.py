from __future__ import annotations

import json
from pathlib import Path
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


def read_adapter_status() -> dict[str, Any]:
    return _read_json(
        EXCHANGE_DIR / "adapter_status.json",
        {
            "ok": False,
            "adapter_online": False,
            "active_source": "NONE",
            "message": "No adapter_status.json found. Start an MBIL adapter first.",
        },
    )


def read_exchange_latest() -> dict[str, Any]:
    return {
        "adapter_status": read_adapter_status(),
        "bus1553_a": _read_json(EXCHANGE_DIR / "bus1553_A_latest.json", {"messages": []}),
        "bus1553_b": _read_json(EXCHANGE_DIR / "bus1553_B_latest.json", {"messages": []}),
        "arinc429": _read_json(EXCHANGE_DIR / "arinc429_latest.json", {"labels": [], "stub": True}),
        "discretes": _read_json(EXCHANGE_DIR / "discretes_latest.json", {"signals": {}, "stub": True}),
        "analog": _read_json(EXCHANGE_DIR / "analog_latest.json", {"channels": {}, "stub": True}),
        "ethernet": _read_json(EXCHANGE_DIR / "ethernet_latest.json", {"packets": [], "stub": True}),
    }
