from __future__ import annotations

import base64
import json
import socket
from pathlib import Path
from time import sleep, time
from typing import Any

from adapters.common.aircraft_truth import AircraftTruth


class DisCaptureRecorder:
    """Records raw DIS UDP datagrams to JSONL capture files.

    Phase 1 records raw packets. If the datagram is JSON telemetry, the source
    can decode it for MBIL immediately. Real binary DIS Entity State PDU decode
    is intentionally a phase-2 parser so the adapter boundary can land safely.
    """

    def __init__(self, capture_dir: str = "data/dis_captures"):
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.path: Path | None = None
        self.enabled = False

    def start(self) -> Path:
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        stamp = time()
        self.path = self.capture_dir / f"dis_capture_{int(stamp)}.jsonl"
        self.enabled = True
        self.path.write_text("")
        return self.path

    def stop(self) -> Path | None:
        self.enabled = False
        return self.path

    def record(self, payload: bytes, addr: tuple[str, int] | None = None) -> None:
        if not self.enabled or not self.path:
            return
        record = {
            "schema": "MBIL-DIS-CAPTURE-1",
            "timestamp": time(),
            "src": list(addr) if addr else None,
            "pdu_b64": base64.b64encode(payload).decode("ascii"),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")


def decode_json_telemetry_or_none(payload: bytes, source: str = "DIS_JSON_TEST") -> AircraftTruth | None:
    try:
        text = payload.decode("utf-8", errors="strict").strip()
        if not text.startswith("{"):
            return None
        data = json.loads(text)
        return AircraftTruth.from_mapping(data, source=source)
    except Exception:
        return None


class DisUdpSource:
    name = "DIS UDP Source"

    def __init__(self, host: str = "0.0.0.0", port: int = 3000):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.last_packet_time = 0.0
        self.last_truth: AircraftTruth | None = None
        self.raw_packets_seen = 0
        self.decoded_packets_seen = 0
        self.last_error = ""

    def start(self) -> None:
        if self.sock:
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

    def stop(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def online(self) -> bool:
        # Source exists if the socket is open; data is fresh if packet recently arrived.
        return self.sock is not None

    def poll(self, recorder: DisCaptureRecorder | None = None) -> AircraftTruth | None:
        if not self.sock:
            self.start()

        assert self.sock is not None
        latest_truth: AircraftTruth | None = None

        while True:
            try:
                payload, addr = self.sock.recvfrom(65535)
            except BlockingIOError:
                break
            except Exception as exc:
                self.last_error = str(exc)
                break

            self.raw_packets_seen += 1
            self.last_packet_time = time()
            if recorder:
                recorder.record(payload, addr)

            truth = decode_json_telemetry_or_none(payload, source="DIS_JSON_TEST")
            if truth:
                self.decoded_packets_seen += 1
                self.last_truth = truth
                latest_truth = truth

        return latest_truth or self.last_truth


class DisReplaySource:
    name = "DIS Capture Replay"

    def __init__(self, path: str | None = None):
        self.path = Path(path) if path else None
        self.records: list[dict[str, Any]] = []
        self.index = 0
        self.last_emit = 0.0
        self.last_truth: AircraftTruth | None = None
        if self.path:
            self.load(str(self.path))

    def load(self, path: str) -> None:
        self.path = Path(path)
        self.records = []
        self.index = 0
        if not self.path.exists():
            return
        for line in self.path.read_text().splitlines():
            try:
                self.records.append(json.loads(line))
            except Exception:
                continue

    def online(self) -> bool:
        return bool(self.records)

    def next_truth(self) -> AircraftTruth | None:
        if not self.records:
            return None
        now = time()
        if now - self.last_emit < 0.20:
            return self.last_truth
        self.last_emit = now

        record = self.records[self.index]
        self.index = (self.index + 1) % len(self.records)
        try:
            payload = base64.b64decode(record.get("pdu_b64", ""))
        except Exception:
            return self.last_truth

        truth = decode_json_telemetry_or_none(payload, source="DIS_REPLAY_JSON_TEST")
        if truth:
            self.last_truth = truth
        return self.last_truth
