from __future__ import annotations

import json
from pathlib import Path
from time import sleep, time

EXCHANGE_DIR = Path("data/exchange")


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def age(path: Path):
    try:
        return time() - path.stat().st_mtime
    except Exception:
        return None


print("Watching data/exchange. Ctrl+C to stop.")
try:
    while True:
        status = read_json(EXCHANGE_DIR / "adapter_status.json") or {}
        bus_a = read_json(EXCHANGE_DIR / "bus1553_A_latest.json") or {"messages": []}
        bus_b = read_json(EXCHANGE_DIR / "bus1553_B_latest.json") or {"messages": []}
        messages = (bus_a.get("messages") or []) + (bus_b.get("messages") or [])
        types = sorted({m.get("message_type") for m in messages if m.get("message_type")})
        a_age = age(EXCHANGE_DIR / "bus1553_A_latest.json")
        age_text = f"{a_age:.2f}s" if a_age is not None else "missing"
        print(
            f"source={status.get('active_source', 'NONE')} "
            f"online={status.get('adapter_online')} "
            f"age={age_text} "
            f"messages={len(messages)} "
            f"types={','.join(types)} "
            f"msg={status.get('message', '')}"
        )
        sleep(1.0)
except KeyboardInterrupt:
    print("Stopped.")
