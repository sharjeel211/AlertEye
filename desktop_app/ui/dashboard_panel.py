"""
Dashboard Metrics Panel - System status, detection statistics, resource usage
"""

import time
import threading
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QProgressBar
)
from PySide6.QtCore import Qt, QTimer

class MetricCard(QWidget):
    """Single metric display card."""

    def __init__(self, label: str, value: str = "—",
                 unit: str = "", accent: str = "#3b82f6", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background: #0c1428; border: 1px solid #162040; border-radius: 6px;"
        )
        self.setMinimumHeight(72)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self.lbl_label = QLabel(label)
        self.lbl_label.setStyleSheet(
            "color: #2a4060; font-size: 9px; font-weight: 700; "
            "letter-spacing: 1.5px; background: transparent; border: none;"
        )

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(
            f"color: {accent}; font-size: 22px; font-weight: 700; "
            "font-family: 'Courier New', monospace; background: transparent; border: none;"
        )

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet(
            "color: #2a4060; font-size: 9px; background: transparent; border: none;"
        )

        layout.addWidget(self.lbl_label)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_unit)

    def set_value(self, value: str):
        self.lbl_value.setText(str(value))

    def set_accent(self, color: str):
        self.lbl_value.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 700; "
            "font-family: 'Courier New', monospace; background: transparent; border: none;"
        )

class DashboardPanel(QWidget):
    """
    Sidebar dashboard with system metrics, detection counts, resource usage.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self._detection_counts = {}
        self._session_start = time.time()

        self._sys_cpu = 0
        self._sys_ram = 0
        self._sys_gpu = -1
        self._sys_lock = threading.Lock()

        self._setup_ui()
        self._start_system_monitor()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        self._add_section_title(layout, "SESSION")
        info_grid = QGridLayout()
        info_grid.setSpacing(6)
        self.card_fps     = MetricCard("ENGINE FPS", "—",  "fps",   "#3b82f6")
        self.card_detects = MetricCard("DETECTIONS", "0",  "total", "#ffd700")
        self.card_alerts  = MetricCard("ALERTS",     "0",  "fired", "#ff3355")
        self.card_uptime  = MetricCard("UPTIME",     "0s", "",      "#5ab4ff")
        info_grid.addWidget(self.card_fps,     0, 0)
        info_grid.addWidget(self.card_detects, 0, 1)
        info_grid.addWidget(self.card_alerts,  1, 0)
        info_grid.addWidget(self.card_uptime,  1, 1)
        layout.addLayout(info_grid)

        self._add_separator(layout)

        self._add_section_title(layout, "SYSTEM")
        self.cpu_row = self._resource_row(layout, "CPU")
        self.ram_row = self._resource_row(layout, "RAM")
        self.gpu_row = self._resource_row(layout, "GPU")

        self._add_separator(layout)

        self._add_section_title(layout, "DETECTION BREAKDOWN")
        self.breakdown_layout = QVBoxLayout()
        self.breakdown_layout.setSpacing(4)
        self._breakdown_labels = {}
        modules = [
            ("weapon_detection",     "⚠  Weapons"),
            ("fire_smoke_detection", "🔥  Fire/Smoke"),
            ("accident_detection",   "💥  Accidents"),
        ]
        for mid, name in modules:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #4a6080; font-size: 10px; background: transparent;")
            val = QLabel("0")
            val.setStyleSheet(
                "color: #2a4060; font-size: 10px; "
                "font-family: 'Courier New'; min-width: 24px; background: transparent;"
            )
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(lbl)
            rl.addStretch()
            rl.addWidget(val)
            self._breakdown_labels[mid] = val
            self.breakdown_layout.addWidget(row)
        layout.addLayout(self.breakdown_layout)

        self._add_separator(layout)

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet(
            "color: #1e3050; font-size: 24px; font-family: 'Courier New'; "
            "font-weight: 700; letter-spacing: 5px; background: transparent;"
        )
        self.date_label = QLabel(datetime.now().strftime("%Y-%m-%d"))
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet(
            "color: #182838; font-size: 10px; letter-spacing: 2px; background: transparent;"
        )
        layout.addWidget(self.clock_label)
        layout.addWidget(self.date_label)
        layout.addStretch()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._apply_resource_ui)
        self._resource_timer.start(2000)

    def _add_section_title(self, layout, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #1e3050; font-size: 9px; font-weight: 700; "
            "letter-spacing: 2.5px; background: transparent;"
        )
        layout.addWidget(lbl)

    def _add_separator(self, layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #0f1828; background: #0f1828; border: none;")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

    def _resource_row(self, parent_layout, name: str):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 2)
        rl.setSpacing(6)
        lbl = QLabel(name)
        lbl.setFixedWidth(30)
        lbl.setStyleSheet("color: #2a4060; font-size: 10px; background: transparent;")
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFixedHeight(5)
        bar.setTextVisible(False)
        bar.setStyleSheet(
            "QProgressBar { background: #0c1828; border: none; border-radius: 2px; } "
            "QProgressBar::chunk { background: #3b82f6; border-radius: 2px; }"
        )
        pct = QLabel("0%")
        pct.setFixedWidth(32)
        pct.setStyleSheet(
            "color: #2a4060; font-size: 9px; font-family: 'Courier New'; background: transparent;"
        )
        pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        rl.addWidget(lbl)
        rl.addWidget(bar, 1)
        rl.addWidget(pct)
        parent_layout.addWidget(row)
        return (bar, pct)

    def _start_system_monitor(self):
        """Background thread only stores values — never touches Qt objects."""
        def _bg_loop():
            while True:
                try:
                    import psutil
                    cpu = int(psutil.cpu_percent(interval=1.5))
                    ram = int(psutil.virtual_memory().percent)
                    gpu = -1
                    try:
                        import GPUtil
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu = int(gpus[0].load * 100)
                    except Exception:
                        pass
                    with self._sys_lock:
                        self._sys_cpu = cpu
                        self._sys_ram = ram
                        self._sys_gpu = gpu
                except Exception:
                    pass
                time.sleep(0.5)

        threading.Thread(target=_bg_loop, daemon=True).start()

    def _apply_resource_ui(self):
        """Called by QTimer on the main thread — safe to touch Qt widgets."""
        with self._sys_lock:
            cpu = self._sys_cpu
            ram = self._sys_ram
            gpu = self._sys_gpu

        for (bar, pct), val in [(self.cpu_row, cpu), (self.ram_row, ram)]:
            bar.setValue(val)
            pct.setText(f"{val}%")
            color = "#ff2244" if val > 90 else "#ff8800" if val > 70 else "#3b82f6"
            bar.setStyleSheet(
                f"QProgressBar {{ background: #0c1828; border: none; border-radius: 2px; }} "
                f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
            )

        if gpu >= 0:
            self.gpu_row[0].setValue(gpu)
            self.gpu_row[1].setText(f"{gpu}%")
            color = "#ff2244" if gpu > 90 else "#ff8800" if gpu > 70 else "#3b82f6"
            self.gpu_row[0].setStyleSheet(
                f"QProgressBar {{ background: #0c1828; border: none; border-radius: 2px; }} "
                f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
            )
        else:
            self.gpu_row[1].setText("N/A")

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        elapsed = int(time.time() - self._session_start)
        if elapsed < 60:
            self.card_uptime.set_value(f"{elapsed}s")
        elif elapsed < 3600:
            self.card_uptime.set_value(f"{elapsed // 60}m")
        else:
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            self.card_uptime.set_value(f"{h}h{m}m")

    def update_fps(self, fps: float):
        self.card_fps.set_value(f"{fps:.0f}")

    def increment_detections(self, module_name: str, count: int = 1):
        current = self._detection_counts.get("total", 0)
        self._detection_counts["total"] = current + count
        self.card_detects.set_value(str(self._detection_counts["total"]))

        mod_count = self._detection_counts.get(module_name, 0) + count
        self._detection_counts[module_name] = mod_count

        if module_name in self._breakdown_labels:
            self._breakdown_labels[module_name].setText(str(mod_count))
            self._breakdown_labels[module_name].setStyleSheet(
                "color: #3b82f6; font-size: 10px; "
                "font-family: 'Courier New'; min-width: 24px; background: transparent;"
            )

    def increment_alerts(self):
        count = self._detection_counts.get("alerts", 0) + 1
        self._detection_counts["alerts"] = count
        self.card_alerts.set_value(str(count))
        self.card_alerts.set_accent("#ff3355")
