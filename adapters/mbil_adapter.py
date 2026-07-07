from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import time

from adapters.common.arinc429_encoder import encode_arinc429_labels
from adapters.common.bus1553_encoder import encode_1553_messages
from adapters.common.file_exchange import (
    ensure_exchange_dirs,
    write_1553_exchange,
    write_adapter_status,
    write_arinc429_exchange,
    write_route_exchange,
)
from adapters.sources.dis import DisCaptureRecorder, DisReplaySource, DisUdpSource
from adapters.sources.synthetic import SyntheticAircraftSource
from adapters.sources.xplane import DEFAULT_BASE_URL as XPLANE_DEFAULT_BASE_URL
from adapters.sources.xplane import XPlaneWebSource


SOURCE_SYNTHETIC = "Synthetic Aircraft Source"
SOURCE_DIS_UDP = "DIS UDP Source"
SOURCE_DIS_REPLAY = "DIS Capture Replay"
SOURCE_XPLANE = "X-Plane Web API Source"
SOURCE_MSFS = "MSFS Stub"
SOURCE_DCS = "DCS Stub"

ALL_SOURCES = [
    SOURCE_SYNTHETIC,
    SOURCE_DIS_UDP,
    SOURCE_DIS_REPLAY,
    SOURCE_XPLANE,
    SOURCE_MSFS,
    SOURCE_DCS,
]

SOURCE_ALIASES = {
    "synthetic": SOURCE_SYNTHETIC,
    "self": SOURCE_SYNTHETIC,
    "self-created": SOURCE_SYNTHETIC,
    "self_created": SOURCE_SYNTHETIC,
    "dis": SOURCE_DIS_UDP,
    "dis-udp": SOURCE_DIS_UDP,
    "dis_udp": SOURCE_DIS_UDP,
    "udp": SOURCE_DIS_UDP,
    "replay": SOURCE_DIS_REPLAY,
    "dis-replay": SOURCE_DIS_REPLAY,
    "xplane": SOURCE_XPLANE,
    "x-plane": SOURCE_XPLANE,
    "msfs": SOURCE_MSFS,
    "dcs": SOURCE_DCS,
}


def normalize_source(value: str) -> str:
    if value in ALL_SOURCES:
        return value
    key = value.strip().lower()
    if key in SOURCE_ALIASES:
        return SOURCE_ALIASES[key]
    valid = ", ".join(sorted(SOURCE_ALIASES))
    raise argparse.ArgumentTypeError(f"Unknown source '{value}'. Try one of: {valid}")


class AdapterCore:
    def __init__(self, dis_port: int = 3000, synthetic_profile: str = "normal", xplane_base_url: str = XPLANE_DEFAULT_BASE_URL):
        ensure_exchange_dirs()
        self.synthetic_profile = synthetic_profile
        self.synthetic = SyntheticAircraftSource(profile=synthetic_profile)
        self.dis_udp = DisUdpSource(port=dis_port)
        self.dis_replay = DisReplaySource()
        self.xplane = XPlaneWebSource(base_url=xplane_base_url)
        self.recorder = DisCaptureRecorder()
        self.translated_dis_recorder = DisCaptureRecorder()
        self.active_source = SOURCE_SYNTHETIC
        self.running = False
        self.tick = 0
        self.last_message = "Adapter initialized."

    def set_source(self, source: str) -> None:
        self.active_source = normalize_source(source)
        self.last_message = f"Selected {self.active_source}."
        if self.active_source == SOURCE_DIS_UDP:
            self.dis_udp.start()

    def load_replay(self, path: str) -> None:
        self.dis_replay.load(path)
        self.active_source = SOURCE_DIS_REPLAY
        self.last_message = f"Loaded replay {path}."

    def start_recording(self) -> Path:
        path = self.recorder.start()
        self.last_message = f"Recording DIS capture to {path}."
        return path

    def stop_recording(self) -> Path | None:
        path = self.recorder.stop()
        self.last_message = f"Stopped DIS recording: {path}."
        return path

    def start_translated_dis_recording(self) -> Path:
        path = self.translated_dis_recorder.start()
        self.last_message = f"Recording translated source replay to {path}."
        return path

    def stop_translated_dis_recording(self) -> Path | None:
        path = self.translated_dis_recorder.stop()
        self.last_message = f"Stopped translated source replay recording: {path}."
        return path

    def record_truth_as_dis_json(self, truth) -> None:
        if not self.translated_dis_recorder.enabled:
            return
        payload = truth.to_dict()
        payload["schema"] = "MBIL-DIS-JSON-TRUTH-1"
        payload["source"] = f"TRANSLATED:{truth.source}"
        payload["adapter_tick"] = self.tick
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.translated_dis_recorder.record(raw, ("MBIL_TRANSLATED", 0))

    def source_online(self, source: str) -> bool:
        if source == SOURCE_SYNTHETIC:
            return True
        if source == SOURCE_DIS_UDP:
            return self.dis_udp.online()
        if source == SOURCE_DIS_REPLAY:
            return self.dis_replay.online()
        if source == SOURCE_XPLANE:
            return self.xplane.online()
        return False

    def status(self) -> dict:
        return {
            "adapter_online": self.running,
            "active_source": self.active_source,
            "available_sources": [
                {"name": source, "online": self.source_online(source)} for source in ALL_SOURCES
            ],
            "synthetic_profile": self.synthetic_profile,
            "recording_dis": self.recorder.enabled,
            "recording_path": str(self.recorder.path) if self.recorder.path else None,
            "recording_translated_dis": self.translated_dis_recorder.enabled,
            "translated_dis_recording_path": str(self.translated_dis_recorder.path) if self.translated_dis_recorder.path else None,
            "xplane": self.xplane.status(),
            "dis_udp": {
                "host": self.dis_udp.host,
                "port": self.dis_udp.port,
                "raw_packets_seen": self.dis_udp.raw_packets_seen,
                "decoded_packets_seen": self.dis_udp.decoded_packets_seen,
                "last_packet_age_sec": round(time() - self.dis_udp.last_packet_time, 2) if self.dis_udp.last_packet_time else None,
                "last_error": self.dis_udp.last_error,
            },
            "message": self.last_message,
        }

    def step(self) -> None:
        self.running = True
        self.tick += 1
        truth = None

        if self.active_source == SOURCE_SYNTHETIC:
            truth = self.synthetic.next_truth()
        elif self.active_source == SOURCE_DIS_UDP:
            truth = self.dis_udp.poll(self.recorder)
            if truth is None:
                self.last_message = "DIS UDP online, but no decoded aircraft state yet. Raw packets can still be recorded."
        elif self.active_source == SOURCE_DIS_REPLAY:
            truth = self.dis_replay.next_truth()
            if truth is None:
                self.last_message = "Replay loaded, but no decoded aircraft state yet. Raw DIS replay decode is phase 2."
        elif self.active_source == SOURCE_XPLANE:
            truth = self.xplane.next_truth()
            if truth is None:
                self.last_message = f"X-Plane Web API unavailable/no data: {self.xplane.last_error}"
        else:
            self.last_message = f"{self.active_source} is stubbed/offline. Select Synthetic, DIS, Replay, or X-Plane."

        if truth is not None:
            self.record_truth_as_dis_json(truth)
            messages = encode_1553_messages(truth, self.tick)
            arinc_labels = encode_arinc429_labels(truth, self.tick)
            self.last_message = f"Wrote {len(messages)} 1553 messages and {len(arinc_labels)} ARINC labels from {truth.source}."
            status = self.status()
            write_1553_exchange(messages, status)
            write_arinc429_exchange(arinc_labels, status)
            write_route_exchange(truth, status)
        else:
            write_adapter_status(self.status())


# GUI is optional so MBIL can still run on a minimal VM.
def run_gui(core: AdapterCore) -> int:
    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import (
            QApplication,
            QComboBox,
            QFileDialog,
            QGridLayout,
            QGroupBox,
            QLabel,
            QMainWindow,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except Exception as exc:
        print("PyQt6 is not installed. Install requirements_adapter.txt or run --headless.")
        print(exc)
        return 2

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("MBIL Source Adapter")
            self.setMinimumWidth(720)

            self.source_combo = QComboBox()
            self.source_combo.addItems(ALL_SOURCES)
            self.source_combo.currentTextChanged.connect(core.set_source)

            self.start_button = QPushButton("Start")
            self.stop_button = QPushButton("Stop")
            self.record_button = QPushButton("Record DIS")
            self.stop_record_button = QPushButton("Stop Record")
            self.replay_button = QPushButton("Load DIS Replay")

            self.status_label = QLabel("Adapter stopped.")
            self.status_label.setWordWrap(True)
            self.source_status = QLabel("")
            self.source_status.setWordWrap(True)

            self.start_button.clicked.connect(self.start)
            self.stop_button.clicked.connect(self.stop)
            self.record_button.clicked.connect(lambda: core.start_recording())
            self.stop_record_button.clicked.connect(lambda: core.stop_recording())
            self.replay_button.clicked.connect(self.load_replay)

            controls = QGroupBox("Source Selection")
            grid = QGridLayout()
            grid.addWidget(QLabel("Active Source"), 0, 0)
            grid.addWidget(self.source_combo, 0, 1, 1, 4)
            grid.addWidget(self.start_button, 1, 0)
            grid.addWidget(self.stop_button, 1, 1)
            grid.addWidget(self.record_button, 1, 2)
            grid.addWidget(self.stop_record_button, 1, 3)
            grid.addWidget(self.replay_button, 1, 4)
            controls.setLayout(grid)

            root = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(controls)
            layout.addWidget(QLabel("Status"))
            layout.addWidget(self.status_label)
            layout.addWidget(QLabel("Sources"))
            layout.addWidget(self.source_status)
            root.setLayout(layout)
            self.setCentralWidget(root)

            self.timer = QTimer()
            self.timer.setInterval(200)
            self.timer.timeout.connect(self.tick)
            self.ui_timer = QTimer()
            self.ui_timer.setInterval(500)
            self.ui_timer.timeout.connect(self.refresh_status)
            self.ui_timer.start()

        def start(self):
            core.running = True
            self.timer.start()
            core.last_message = "Adapter running."

        def stop(self):
            core.running = False
            self.timer.stop()
            core.last_message = "Adapter stopped."
            write_adapter_status(core.status())

        def load_replay(self):
            path, _ = QFileDialog.getOpenFileName(self, "Open DIS Capture", "data/dis_captures", "DIS captures (*.jsonl);;All files (*)")
            if path:
                core.load_replay(path)
                self.source_combo.setCurrentText(SOURCE_DIS_REPLAY)

        def tick(self):
            core.step()
            self.refresh_status()

        def refresh_status(self):
            status = core.status()
            self.status_label.setText(status["message"])
            lines = []
            for item in status["available_sources"]:
                marker = "ONLINE" if item["online"] else "OFFLINE"
                lines.append(f"[{marker}] {item['name']}")
            lines.append(f"DIS raw packets: {status['dis_udp']['raw_packets_seen']}")
            lines.append(f"DIS decoded packets: {status['dis_udp']['decoded_packets_seen']}")
            lines.append(f"Recording raw DIS: {status['recording_dis']}")
            lines.append(f"Recording translated replay: {status['recording_translated_dis']}")
            self.source_status.setText("\n".join(lines))
            write_adapter_status(status)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def run_headless(core: AdapterCore, record_dis: bool = False, record_translated_dis: bool = False) -> int:
    print(f"MBIL adapter running headless. Active source: {core.active_source}. Ctrl+C to stop.")
    if record_dis:
        path = core.start_recording()
        print(f"Recording raw DIS UDP capture to {path}")
    if record_translated_dis:
        path = core.start_translated_dis_recording()
        print(f"Recording translated source DIS JSON replay to {path}")
    core.running = True
    last_print = 0.0
    try:
        while True:
            core.step()
            now = time()
            if now - last_print >= 2.0:
                last_print = now
                status = core.status()
                dis = status["dis_udp"]
                extra = " translated_rec=" + str(status.get("recording_translated_dis", False))
                print(
                    f"{status['active_source']} | {status['message']} | "
                    f"DIS raw={dis['raw_packets_seen']} decoded={dis['decoded_packets_seen']}" + extra
                )
            from time import sleep
            sleep(0.2)
    except KeyboardInterrupt:
        core.running = False
        if record_dis:
            core.stop_recording()
        if record_translated_dis:
            core.stop_translated_dis_recording()
        write_adapter_status(core.status())
        print("Stopped.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MBIL source adapter switchboard")
    parser.add_argument("--headless", action="store_true", help="Run without PyQt GUI")
    parser.add_argument(
        "--source",
        default="synthetic",
        type=normalize_source,
        help="Initial source. Easy values: synthetic, dis, replay, xplane, msfs, dcs",
    )
    parser.add_argument("--dis-port", type=int, default=3000, help="DIS UDP listen port")
    parser.add_argument("--xplane-base-url", default=XPLANE_DEFAULT_BASE_URL, help="X-Plane Web API base URL")
    parser.add_argument("--replay", help="DIS capture JSONL replay file")
    parser.add_argument("--record-dis", action="store_true", help="Record raw DIS UDP packets while running headless")
    parser.add_argument("--record-translated-dis", action="store_true", help="Record the selected source as replayable MBIL DIS JSON packets")
    parser.add_argument(
        "--profile",
        default="normal",
        choices=["normal", "low-level", "terrain-caution", "terrain-pull-up"],
        help="Synthetic source profile for testing normal, low-level, caution, or pull-up TAWS cases.",
    )
    args = parser.parse_args()

    core = AdapterCore(dis_port=args.dis_port, synthetic_profile=args.profile, xplane_base_url=args.xplane_base_url)
    if args.replay:
        core.load_replay(args.replay)
    else:
        core.set_source(args.source)

    if args.headless:
        return run_headless(core, record_dis=args.record_dis, record_translated_dis=args.record_translated_dis)
    return run_gui(core)


if __name__ == "__main__":
    raise SystemExit(main())
