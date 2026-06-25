from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import time

from adapters.common.bus1553_encoder import encode_1553_messages
from adapters.common.file_exchange import ensure_exchange_dirs, write_1553_exchange, write_adapter_status
from adapters.sources.dis import DisCaptureRecorder, DisReplaySource, DisUdpSource
from adapters.sources.synthetic import SyntheticAircraftSource


SOURCE_SYNTHETIC = "Synthetic Aircraft Source"
SOURCE_DIS_UDP = "DIS UDP Source"
SOURCE_DIS_REPLAY = "DIS Capture Replay"
SOURCE_XPLANE = "X-Plane Stub"
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


class AdapterCore:
    def __init__(self, dis_port: int = 3000):
        ensure_exchange_dirs()
        self.synthetic = SyntheticAircraftSource()
        self.dis_udp = DisUdpSource(port=dis_port)
        self.dis_replay = DisReplaySource()
        self.recorder = DisCaptureRecorder()
        self.active_source = SOURCE_SYNTHETIC
        self.running = False
        self.tick = 0
        self.last_message = "Adapter initialized."

    def set_source(self, source: str) -> None:
        self.active_source = source
        self.last_message = f"Selected {source}."
        if source == SOURCE_DIS_UDP:
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

    def source_online(self, source: str) -> bool:
        if source == SOURCE_SYNTHETIC:
            return True
        if source == SOURCE_DIS_UDP:
            return self.dis_udp.online()
        if source == SOURCE_DIS_REPLAY:
            return self.dis_replay.online()
        return False

    def status(self) -> dict:
        return {
            "adapter_online": self.running,
            "active_source": self.active_source,
            "available_sources": [
                {"name": source, "online": self.source_online(source)} for source in ALL_SOURCES
            ],
            "recording_dis": self.recorder.enabled,
            "recording_path": str(self.recorder.path) if self.recorder.path else None,
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
        else:
            self.last_message = f"{self.active_source} is stubbed/offline. Select Synthetic or DIS."

        if truth is not None:
            messages = encode_1553_messages(truth, self.tick)
            self.last_message = f"Wrote {len(messages)} 1553-style messages from {truth.source}."
            write_1553_exchange(messages, self.status())
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
            lines.append(f"Recording: {status['recording_dis']}")
            self.source_status.setText("\n".join(lines))
            write_adapter_status(status)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def run_headless(core: AdapterCore) -> int:
    print("MBIL adapter running headless. Ctrl+C to stop.")
    core.running = True
    try:
        while True:
            core.step()
            from time import sleep
            sleep(0.2)
    except KeyboardInterrupt:
        core.running = False
        write_adapter_status(core.status())
        print("Stopped.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MBIL source adapter switchboard")
    parser.add_argument("--headless", action="store_true", help="Run without PyQt GUI")
    parser.add_argument("--source", default=SOURCE_SYNTHETIC, choices=ALL_SOURCES, help="Initial source")
    parser.add_argument("--dis-port", type=int, default=3000, help="DIS UDP listen port")
    parser.add_argument("--replay", help="DIS capture JSONL replay file")
    args = parser.parse_args()

    core = AdapterCore(dis_port=args.dis_port)
    if args.replay:
        core.load_replay(args.replay)
    else:
        core.set_source(args.source)

    if args.headless:
        return run_headless(core)
    return run_gui(core)


if __name__ == "__main__":
    raise SystemExit(main())
