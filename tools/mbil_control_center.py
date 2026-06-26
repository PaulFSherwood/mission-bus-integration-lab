from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

try:
    from PyQt6.QtCore import QProcess, QProcessEnvironment, QTimer, Qt
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFileDialog,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QSpinBox,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except Exception as exc:  # pragma: no cover - this is a launcher script
    print("PyQt6 is required for MBIL Control Center.")
    print("Install with: pip install -r requirements_adapter.txt")
    print(exc)
    raise


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = sys.executable


class ManagedProcess:
    def __init__(self, name: str, log: QPlainTextEdit, status_label: QLabel):
        self.name = name
        self.log = log
        self.status_label = status_label
        self.proc = QProcess()
        self.proc.setWorkingDirectory(str(PROJECT_ROOT))
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_output)
        self.proc.started.connect(self._started)
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(self._error)

    def is_running(self) -> bool:
        return self.proc.state() != QProcess.ProcessState.NotRunning

    def start(self, program: str, args: list[str], extra_env: dict[str, str] | None = None) -> None:
        if self.is_running():
            self.append(f"{self.name} is already running.")
            return

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        if extra_env:
            for key, value in extra_env.items():
                env.insert(key, value)
        self.proc.setProcessEnvironment(env)

        self.append("$ " + " ".join([program] + args))
        self.proc.start(program, args)

    def stop(self) -> None:
        if not self.is_running():
            self.append(f"{self.name} is not running.")
            return
        self.append(f"Stopping {self.name}...")
        self.proc.terminate()
        QTimer.singleShot(3000, self._kill_if_needed)

    def _kill_if_needed(self) -> None:
        if self.is_running():
            self.append(f"{self.name} did not exit; killing it.")
            self.proc.kill()

    def append(self, text: str) -> None:
        self.log.appendPlainText(f"[{self.name}] {text}")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _read_output(self) -> None:
        data = bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        if data.strip():
            for line in data.rstrip().splitlines():
                self.append(line)

    def _started(self) -> None:
        self.status_label.setText(f"{self.name}: RUNNING")
        self.status_label.setProperty("state", "running")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        status = "CRASHED" if exit_status == QProcess.ExitStatus.CrashExit else f"STOPPED ({exit_code})"
        self.status_label.setText(f"{self.name}: {status}")
        self.status_label.setProperty("state", "stopped")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.append(f"Process finished: {status}")

    def _error(self, error) -> None:
        self.append(f"Process error: {error}")


class MbilControlCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MBIL Control Center")
        self.setMinimumSize(1100, 760)

        self.adapter_log = QPlainTextEdit()
        self.mbil_log = QPlainTextEdit()
        self.watch_log = QPlainTextEdit()
        self.command_log = QPlainTextEdit()
        for log in [self.adapter_log, self.mbil_log, self.watch_log, self.command_log]:
            log.setReadOnly(True)
            log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.adapter_status = QLabel("Adapter: STOPPED")
        self.mbil_status = QLabel("MBIL Web: STOPPED")
        self.watch_status = QLabel("Exchange Watch: STOPPED")

        self.adapter = ManagedProcess("Adapter", self.adapter_log, self.adapter_status)
        self.mbil = ManagedProcess("MBIL Web", self.mbil_log, self.mbil_status)
        self.watch = ManagedProcess("Exchange Watch", self.watch_log, self.watch_status)
        self.command = ManagedProcess("Command", self.command_log, QLabel("Command: IDLE"))

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        title = QLabel("MBIL Control Center")
        title.setObjectName("Title")
        subtitle = QLabel("Start the adapter, MBIL web server, exchange watcher, DIS test sender, and browser pages from one place.")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        status_row = QHBoxLayout()
        status_row.addWidget(self.adapter_status)
        status_row.addWidget(self.mbil_status)
        status_row.addWidget(self.watch_status)
        layout.addLayout(status_row)

        controls = QHBoxLayout()
        controls.addWidget(self._adapter_group(), 2)
        controls.addWidget(self._mbil_group(), 2)
        controls.addWidget(self._quick_group(), 1)
        layout.addLayout(controls)

        tabs = QTabWidget()
        tabs.addTab(self.adapter_log, "Adapter Log")
        tabs.addTab(self.mbil_log, "MBIL Web Log")
        tabs.addTab(self.watch_log, "Exchange Watch")
        tabs.addTab(self.command_log, "Commands")
        layout.addWidget(tabs, 1)

        self.setCentralWidget(root)

    def _adapter_group(self) -> QGroupBox:
        box = QGroupBox("Adapter")
        grid = QGridLayout(box)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["synthetic", "dis", "replay", "xplane", "msfs", "dcs"])

        self.synthetic_profile = QComboBox()
        self.synthetic_profile.addItems(["normal", "low-level", "terrain-caution", "terrain-pull-up"])

        self.dis_port = QSpinBox()
        self.dis_port.setRange(1, 65535)
        self.dis_port.setValue(3000)

        self.record_dis = QCheckBox("Record DIS packets")
        self.replay_path = QLineEdit()
        self.replay_path.setPlaceholderText("data/dis_captures/example.jsonl")
        browse_replay = QPushButton("Browse Replay")
        browse_replay.clicked.connect(self.browse_replay)

        start = QPushButton("Start Adapter")
        stop = QPushButton("Stop Adapter")
        start.clicked.connect(self.start_adapter)
        stop.clicked.connect(self.adapter.stop)

        grid.addWidget(QLabel("Source"), 0, 0)
        grid.addWidget(self.source_combo, 0, 1, 1, 2)
        grid.addWidget(QLabel("Synthetic Profile"), 1, 0)
        grid.addWidget(self.synthetic_profile, 1, 1, 1, 2)
        grid.addWidget(QLabel("DIS UDP Port"), 2, 0)
        grid.addWidget(self.dis_port, 2, 1, 1, 2)
        grid.addWidget(self.record_dis, 3, 1, 1, 2)
        grid.addWidget(QLabel("Replay File"), 4, 0)
        grid.addWidget(self.replay_path, 4, 1)
        grid.addWidget(browse_replay, 4, 2)
        grid.addWidget(start, 5, 1)
        grid.addWidget(stop, 5, 2)
        return box

    def _mbil_group(self) -> QGroupBox:
        box = QGroupBox("MBIL Web")
        grid = QGridLayout(box)

        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(8000)
        self.input_mode = QComboBox()
        self.input_mode.addItems(["auto", "exchange", "internal"])
        self.reload = QCheckBox("--reload")
        self.reload.setChecked(True)

        start = QPushButton("Start MBIL Web")
        stop = QPushButton("Stop MBIL Web")
        start.clicked.connect(self.start_mbil)
        stop.clicked.connect(self.mbil.stop)

        grid.addWidget(QLabel("Host"), 0, 0)
        grid.addWidget(self.host, 0, 1)
        grid.addWidget(QLabel("Port"), 1, 0)
        grid.addWidget(self.port, 1, 1)
        grid.addWidget(QLabel("Input Mode"), 2, 0)
        grid.addWidget(self.input_mode, 2, 1)
        grid.addWidget(self.reload, 3, 1)
        grid.addWidget(start, 4, 0)
        grid.addWidget(stop, 4, 1)
        return box

    def _quick_group(self) -> QGroupBox:
        box = QGroupBox("Quick Actions")
        layout = QVBoxLayout(box)

        start_stack = QPushButton("Start Stack")
        stop_all = QPushButton("Stop All")
        start_watch = QPushButton("Start Exchange Watch")
        stop_watch = QPushButton("Stop Exchange Watch")
        send_dis = QPushButton("Send DIS JSON Test")
        overview = QPushButton("Open Cockpit")
        taws = QPushButton("Open TAWS / Weather")
        api_status = QPushButton("Open /api/input/status")

        start_stack.clicked.connect(self.start_stack)
        stop_all.clicked.connect(self.stop_all)
        start_watch.clicked.connect(self.start_watch)
        stop_watch.clicked.connect(self.watch.stop)
        send_dis.clicked.connect(self.send_dis_test)
        overview.clicked.connect(lambda: self.open_url("/overview"))
        taws.clicked.connect(lambda: self.open_url("/taws-weather"))
        api_status.clicked.connect(lambda: self.open_url("/api/input/status"))

        for btn in [start_stack, stop_all, start_watch, stop_watch, send_dis, overview, taws, api_status]:
            layout.addWidget(btn)
        layout.addStretch(1)
        return box

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background: #071018; color: #d8e8f5; font-size: 12px; }
            QLabel#Title { color: #31b7ff; font-size: 24px; font-weight: 900; letter-spacing: 1px; }
            QLabel#Subtitle { color: #9eb7c9; margin-bottom: 8px; }
            QGroupBox { border: 1px solid rgba(120, 180, 220, 0.35); margin-top: 10px; padding: 10px; font-weight: 800; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #31b7ff; }
            QPushButton { background: #14202a; border: 1px solid #31495a; padding: 7px 9px; border-radius: 4px; font-weight: 800; }
            QPushButton:hover { background: #1b3445; }
            QLineEdit, QComboBox, QSpinBox { background: #02070b; border: 1px solid #31495a; padding: 5px; }
            QPlainTextEdit { background: #02070b; border: 1px solid #31495a; color: #d8e8f5; font-family: monospace; }
            QLabel[state="running"] { color: #6dff7d; font-weight: 900; }
            QLabel[state="stopped"] { color: #ffb14d; font-weight: 900; }
            """
        )

    def browse_replay(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open DIS Capture Replay",
            str(PROJECT_ROOT / "data" / "dis_captures"),
            "DIS Capture (*.jsonl);;All Files (*)",
        )
        if path:
            self.replay_path.setText(path)
            self.source_combo.setCurrentText("replay")

    def start_adapter(self) -> None:
        source = self.source_combo.currentText()
        args = [
            "-m", "adapters.mbil_adapter",
            "--headless",
            "--source", source,
            "--profile", self.synthetic_profile.currentText(),
            "--dis-port", str(self.dis_port.value()),
        ]
        if self.record_dis.isChecked():
            args.append("--record-dis")
        if source == "replay":
            replay = self.replay_path.text().strip()
            if not replay:
                QMessageBox.warning(self, "Replay file needed", "Choose a DIS replay file first.")
                return
            args.extend(["--replay", replay])
        self.adapter.start(PYTHON_EXE, args)

    def start_mbil(self) -> None:
        args = ["-m", "uvicorn", "app.main:app", "--host", self.host.text().strip(), "--port", str(self.port.value())]
        if self.reload.isChecked():
            args.append("--reload")
        self.mbil.start(PYTHON_EXE, args, extra_env={"MBIL_INPUT_MODE": self.input_mode.currentText()})

    def start_watch(self) -> None:
        self.watch.start(PYTHON_EXE, ["tools/watch_exchange.py"])

    def send_dis_test(self) -> None:
        if self.command.is_running():
            self.command.append("Command process is busy.")
            return
        self.command.start(PYTHON_EXE, ["tools/send_json_dis_test.py"])

    def start_stack(self) -> None:
        self.start_adapter()
        self.start_mbil()
        self.start_watch()

    def stop_all(self) -> None:
        self.watch.stop()
        self.mbil.stop()
        self.adapter.stop()

    def open_url(self, path: str) -> None:
        host = "127.0.0.1"
        port = self.port.value()
        url = f"http://{host}:{port}{path}"
        self.command_log.appendPlainText(f"[Browser] {url}")
        webbrowser.open(url)

    def closeEvent(self, event):
        if self.adapter.is_running() or self.mbil.is_running() or self.watch.is_running():
            reply = QMessageBox.question(
                self,
                "Stop running processes?",
                "Adapter/MBIL/watch processes are still running. Stop them before exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_all()
        event.accept()


def main() -> int:
    os.chdir(PROJECT_ROOT)
    app = QApplication(sys.argv)
    window = MbilControlCenter()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
