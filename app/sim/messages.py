from dataclasses import dataclass, field
from time import time
from typing import Any

@dataclass
class Bus1553Message:
    tick: int
    timestamp: float
    bus: str
    controller: str
    rt: str
    subaddress: int
    direction: str
    word_count: int
    message_type: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "timestamp": round(self.timestamp, 3),
            "bus": self.bus,
            "controller": self.controller,
            "rt": self.rt,
            "subaddress": self.subaddress,
            "direction": self.direction,
            "word_count": self.word_count,
            "message_type": self.message_type,
            "status": self.status,
            "payload": self.payload,
        }

def make_message(
    *,
    tick: int,
    bus: str,
    controller: str,
    rt: str,
    subaddress: int,
    direction: str,
    word_count: int,
    message_type: str,
    status: str = "OK",
    payload: dict | None = None,
) -> Bus1553Message:
    return Bus1553Message(
        tick=tick,
        timestamp=time(),
        bus=bus,
        controller=controller,
        rt=rt,
        subaddress=subaddress,
        direction=direction,
        word_count=word_count,
        message_type=message_type,
        status=status,
        payload=payload or {},
    )
