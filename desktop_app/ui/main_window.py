"""
Main Window - AlertEye Surveillance System v2.0
FIXED:
  - _apply_subscription_gates: when no auth, enable ALL modules by default
  - DetectionWorker: use get_latest_frame for video files to avoid stalling
  - _on_detection_result: always update video frame even with no detections
  - Module toggle: short name alias forwarded to engine
"""

import os
import cv2
import threading
import numpy as np
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog,
    QInputDialog, QMessageBox, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, Slot
from PySide6.QtGui import QCloseEvent, QPixmap

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
)

from ui.styles import get_stylesheet
from ui.video_widget import VideoFeedWidget
from ui.detection_log_widget import AlertLogWidget, ModuleStatusPanel
from ui.dashboard_panel import DashboardPanel
from core.camera_stream import CameraStream
from core.detection_engine import DetectionEngine, EngineResult
from utils.alert_manager import AlertManager
from utils.logger import get_logger

logger = get_logger("main_window")

AVAILABLE_MODULES = ['fire_smoke', 'weapon', 'accident']

class DetectionWorker(QThread):
    result_ready  = Signal(object)
    status_update = Signal(bool, float, tuple)

    def __init__(self, stream, engine, alert_manager=None):
        super().__init__()
        self.stream   = stream
        self.engine   = engine
        self.alert_manager = alert_manager
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            ret, frame = self.stream.read()
            if not ret or frame is None:
                self.status_update.emit(False, 0.0, (0, 0))
                self.msleep(30)
                continue
            result = self.engine.process_frame(frame)
            if result is not None:
                if getattr(result, "any_alert", False) and self.alert_manager:
                    self.alert_manager.ring_alarm()
                self.result_ready.emit(result)
            else:

                dummy_result = type('R', (), {
                    'annotated_frame': frame,
                    'fps': self.stream.fps,
                    'any_alert': False,
                    'results': {},
                    'frame': frame
                })()
                self.result_ready.emit(dummy_result)
            self.status_update.emit(True, self.stream.fps, self.stream.resolution)

    def stop(self):
        self._running = False
        self.wait(3000)

class MainWindow(QMainWindow):

    def __init__(self, config, auth=None):
        super().__init__()
        self.config  = config
        self.auth    = auth
        self._theme  = "dark"
        self._stream   = None
        self._worker   = None
        self._engine   = None
        self._alert_manager    = None
        self._firebase_notifier = None
        self._is_streaming   = False
        self._camera_name    = "CAM-01"

        self._confirm_seconds   = 1.5
        self._streak_gap        = 4.0
        self._alert_streak_start = {}
        self._alert_last_seen    = {}
        self._alert_call_fired   = {}

        self._apply_theme()
        self._init_systems()
        self._setup_ui()
        self._apply_subscription_gates()
        self._check_first_run()

        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._check_subscription)
        self._heartbeat_timer.start(1_800_000)

        logger.info("Main window initialized.")

    def _apply_theme(self):
        self.setStyleSheet(get_stylesheet(self._theme))

    def _init_systems(self):
        self._alert_manager = AlertManager(self.config)
        self._engine = DetectionEngine(self.config, on_result=None)
        threading.Thread(
            target=lambda: self._engine.initialize(self._on_engine_progress),
            daemon=True
        ).start()
        try:
            from utils.firebase_notifier import FirebaseNotifier
            self._firebase_notifier = FirebaseNotifier()
        except Exception as e:
            logger.warning(f"Firebase notifier unavailable: {e}")

    def _on_engine_progress(self, module_name, current, total):
        logger.debug(f"Engine: {module_name} {current}/{total}")

    def _apply_subscription_gates(self):
        """
        FIX: When there is no auth (running without web portal) or
        subscription is active, enable ALL modules. Only lock them
        when subscription is explicitly expired.
        """
        if not self.auth:

            for mod in AVAILABLE_MODULES:
                self.module_panel.set_module_locked(mod, False)
                if self._engine:
                    self._engine.set_module_enabled(mod, True)
            self.setWindowTitle("AlertEye v2.0 — Standalone Mode")
            return

        enabled = self.auth.enabled_modules
        active  = self.auth.is_subscription_active

        for mod in AVAILABLE_MODULES:

            if active:
                allowed = len(enabled) == 0 or mod in enabled
            else:
                allowed = False
            self.module_panel.set_module_locked(mod, not allowed)
            if self._engine:
                self._engine.set_module_enabled(mod, allowed)

        if not active:
            self._show_expired_banner()

        days = self.auth.days_remaining
        tag  = f"Active · {days}d" if active else "EXPIRED"
        self.setWindowTitle(f"AlertEye v2.0  —  {self.auth.user_name}  ·  {tag}")

    def _show_expired_banner(self):
        if hasattr(self, '_banner_shown'):
            return
        self._banner_shown = True
        banner = QLabel(
            "Subscription expired — all modules locked. "
            "Contact your administrator to renew."
        )
        banner.setStyleSheet(
            "background:#7f1d1d; color:#fca5a5; padding:8px 16px; "
            "font-weight:600; font-size:12px;"
        )
        banner.setAlignment(Qt.AlignCenter)
        c = self.centralWidget()
        if c and c.layout():
            c.layout().insertWidget(0, banner)

    def _check_subscription(self):
        if self.auth:
            self.auth.force_check()
            QTimer.singleShot(3000, self._apply_subscription_gates)

    def _setup_ui(self):
        self.setWindowTitle("AlertEye — AI Powered. Always Watching. v2.0")
        self.setMinimumSize(1200, 720)
        self.resize(1400, 860)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        body = QWidget()
        bl   = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        bl.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.stack.setObjectName("main_content")
        self.live_page     = self._build_live_page()
        self.log_page      = self._build_log_page()
        self.about_page    = self._build_about_page()
        for p in [self.live_page, self.log_page, self.about_page]:
            self.stack.addWidget(p)
        bl.addWidget(self.stack, 1)
        root.addWidget(body, 1)
        self._setup_statusbar()

    def _build_topbar(self):
        bar = QWidget()
        bar.setObjectName("topbar")
        bar.setFixedHeight(54)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(12)

        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        pix = QPixmap(logo_path)
        if not pix.isNull():
            logo_img = QLabel()
            logo_img.setPixmap(pix.scaledToHeight(40, Qt.SmoothTransformation))
            logo_img.setStyleSheet("background: transparent;")
            lay.addWidget(logo_img)
        else:
            logo = QLabel("ALERTEYE")
            logo.setObjectName("topbar_logo")
            lay.addWidget(logo)
        lay.addStretch()

        if self.auth and self.auth.is_logged_in:
            active = self.auth.is_subscription_active
            col    = "#10b981" if active else "#ef4444"
            lbl    = QLabel(
                f"<span style='opacity:.7'>{self.auth.user_name}</span>"
                f"  <span style='color:{col}; font-weight:600;'>"
                f"{'Active' if active else 'Expired'} · {self.auth.days_remaining}d</span>"
            )
            lbl.setObjectName("topbar_user")
            lay.addWidget(lbl)

        if self.auth:
            btn_out = QPushButton("Sign Out")
            btn_out.setObjectName("btn_danger_sm")
            btn_out.setFixedHeight(28)
            btn_out.clicked.connect(self._logout)
            lay.addWidget(btn_out)

        return bar

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._nav_buttons = []
        for label, idx in [("Live Feed", 0), ("Detection Log", 1),
                            ("About", 2)]:
            btn = QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setProperty("active", idx == 0)
            btn.clicked.connect(lambda _, i=idx: self._navigate(i))
            self._nav_buttons.append(btn)
            lay.addWidget(btn)

        lay.addStretch()
        self.module_panel = ModuleStatusPanel()
        self.module_panel.module_toggled.connect(self._on_module_toggle)
        lay.addWidget(self.module_panel)

        foot = QWidget()
        foot.setObjectName("status_panel")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(10, 8, 10, 8)
        self.status_dot  = QLabel("●")
        self.status_text = QLabel("SYSTEM READY")
        self.status_dot.setObjectName("status_dot_label")
        self.status_text.setObjectName("status_text_label")
        fl.addWidget(self.status_dot)
        fl.addWidget(self.status_text)
        fl.addStretch()
        lay.addWidget(foot)
        return sidebar

    def _build_live_page(self):
        page = QWidget()
        lay  = QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(8)

        self.video_widget = VideoFeedWidget()
        self.video_widget.btn_start.clicked.connect(self._start_stream)
        self.video_widget.btn_stop.clicked.connect(self._stop_stream)
        self.video_widget.btn_snapshot.clicked.connect(self._take_snapshot)
        self.video_widget.btn_stop_alarm.clicked.connect(self._stop_alarm)

        self.alert_log = AlertLogWidget()
        self.alert_log.setFixedHeight(200)

        cl.addWidget(self.video_widget, 1)
        cl.addWidget(self.alert_log)

        self.dashboard = DashboardPanel()
        lay.addWidget(center, 1)
        lay.addWidget(self.dashboard)
        return page

    def _build_log_page(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)
        t = QLabel("FULL DETECTION HISTORY")
        t.setObjectName("section_title")
        self.full_log = AlertLogWidget()
        lay.addWidget(t)
        lay.addWidget(self.full_log, 1)
        return page

    def _build_about_page(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setAlignment(Qt.AlignTop)

        if self.auth and self.auth.is_logged_in:
            box = QWidget()
            box.setObjectName("sub_info_box")
            bl  = QVBoxLayout(box)
            bl.setContentsMargins(20, 16, 20, 16)
            active = self.auth.is_subscription_active
            col    = "#10b981" if active else "#ef4444"
            lbl    = QLabel(
                f"<b style='font-size:15px;'>User: {self.auth.user_name}</b><br>"
                f"<span style='color:{col}'>{'Active' if active else 'Expired'}</span>"
                f" subscription · <b>{self.auth.days_remaining}</b> days remaining<br>"
                f"<span style='color:#64748b;font-size:11px;'>"
                f"Modules: {', '.join(self.auth.enabled_modules) or 'All'}</span>"
            )
            lbl.setWordWrap(True)
            bl.addWidget(lbl)
            lay.addWidget(box)
            lay.addSpacing(20)

        about = QLabel(
            "<h2 style='letter-spacing:3px;'>ALERTEYE v2.0</h2>"
            "<p style='color:#64748b;'>AI Powered. Always Watching.</p><br>"
            "<h4>DETECTION MODULES</h4>"
            "<ul style='line-height:2.2;'>"
            "<li>Weapon Detection</li>"
            "<li>Fire &amp; Smoke Detection</li>"
            "<li>Accident Detection</li>"
            "</ul>"
            "<br><h4>ALERTS</h4>"
            "<ul style='line-height:2.2;'>"
            "<li>Sound alarm + screenshot</li>"
            "<li>Email notification</li>"
            "</ul>"
        )
        about.setWordWrap(True)
        about.setObjectName("about_text")
        lay.addWidget(about)
        lay.addStretch()
        return page

    def _setup_statusbar(self):
        bar = self.statusBar()
        bar.setObjectName("status_bar")
        self.sb_camera = QLabel("Camera: —")
        self.sb_fps    = QLabel("FPS: —")
        self.sb_device = QLabel("Device: —")
        self.sb_time   = QLabel("")
        for w in [self.sb_camera, self.sb_fps, self.sb_device]:
            bar.addWidget(w)
        bar.addPermanentWidget(self.sb_time)
        try:
            import torch
            if torch.cuda.is_available():
                self.sb_device.setText(f"GPU: {torch.cuda.get_device_name(0)[:22]}")
            else:
                self.sb_device.setText("Device: CPU")
        except ImportError:
            self.sb_device.setText("Device: CPU")
        t = QTimer(self)
        t.timeout.connect(
            lambda: self.sb_time.setText(datetime.now().strftime("  %Y-%m-%d  %H:%M:%S  "))
        )
        t.start(1000)

    def _navigate(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", i == idx)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _start_stream(self):
        if self._is_streaming:
            return

        if not self._engine or not getattr(self._engine, "_initialized", False):
            QMessageBox.information(
                self, "Loading models",
                "Detection models are still loading. Please wait a few "
                "seconds and try again."
            )
            return
        source = self._get_camera_source()
        if not source:
            return
        self._stream = CameraStream(source, name=self._camera_name)
        if not self._stream.start():
            QMessageBox.warning(self, "Camera Error",
                                f"Could not open: {source}\n{self._stream.error}")
            return
        self._worker = DetectionWorker(self._stream, self._engine, self._alert_manager)
        self._worker.result_ready.connect(self._on_detection_result)
        self._worker.status_update.connect(self._on_stream_status)
        self._worker.start()
        self._is_streaming = True
        self.video_widget.btn_start.setEnabled(False)
        self.video_widget.btn_stop.setEnabled(True)
        self._update_status("STREAMING", "#10b981")

    def _stop_stream(self):
        if not self._is_streaming:
            return
        if self._worker:
            self._worker.stop(); self._worker = None
        if self._stream:
            self._stream.stop();  self._stream = None
        self._is_streaming = False
        self.video_widget.btn_start.setEnabled(True)
        self.video_widget.btn_stop.setEnabled(False)
        self.video_widget.set_offline()
        self._update_status("SYSTEM READY", "#64748b")

    def _get_camera_source(self):
        data = self.video_widget.get_selected_source()
        if data == "rtsp://":
            url, ok = QInputDialog.getText(
                self, "RTSP Stream", "Enter RTSP/IP Camera URL:",
                text="rtsp://admin:password@192.168.1.100:554/stream"
            )
            return url if ok and url else None
        if data == "file":
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Video File", "",
                "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
            )
            return path if path else None
        return data

    @Slot(object)
    def _on_detection_result(self, result):

        if hasattr(result, 'annotated_frame') and result.annotated_frame is not None:
            self.video_widget.update_frame(result.annotated_frame)

        fps = getattr(result, 'fps', 0.0)
        any_alert = getattr(result, 'any_alert', False)

        self.dashboard.update_fps(fps)
        self.sb_fps.setText(f"FPS: {fps:.0f}")
        self.video_widget.update_overlay(self._camera_name, fps, any_alert)

        results = getattr(result, 'results', {})
        for mod, det in results.items():
            if not det.has_detections:
                continue
            for d in det.detections:
                for log in [self.alert_log, self.full_log]:
                    log.add_detection(
                        module_name=mod, label=d.label,
                        confidence=d.confidence, threat_level=d.threat_level,
                        camera_id=self._camera_name
                    )
            self.dashboard.increment_detections(mod, len(det.detections))
            self.module_panel.set_module_alert(mod, det.alert_triggered)
            if det.alert_triggered:
                self._alert_manager.trigger_alert(
                    alert_type=mod, confidence=det.max_confidence,
                    frame=result.frame, camera_id=self._camera_name,
                    metadata={"label": det.detections[0].label}
                )
                self.dashboard.increment_alerts()
                self.video_widget.trigger_alert(True)

                if self._confirm_alert(mod):
                    self._fire_external_alerts(mod, det.max_confidence, result.frame)

    def _confirm_alert(self, alert_type) -> bool:
        """
        Track how long an alert type has been continuously detected.

        Returns True exactly once per streak — the moment the threat has
        persisted for `_confirm_seconds`. A gap longer than `_streak_gap`
        with no detection ends the streak and re-arms confirmation.
        """
        import time
        now  = time.time()
        last = self._alert_last_seen.get(alert_type, 0)

        if alert_type not in self._alert_streak_start or (now - last) > self._streak_gap:
            self._alert_streak_start[alert_type] = now
            self._alert_call_fired[alert_type]   = False
            remaining = int(self._confirm_seconds)
            self.statusBar().showMessage(
                f"⚠ {alert_type.replace('_', ' ').title()} detected — "
                f"confirming threat, calling in {remaining}s…", 5000
            )

        self._alert_last_seen[alert_type] = now
        elapsed = now - self._alert_streak_start[alert_type]

        if not self._alert_call_fired.get(alert_type, False) and elapsed >= self._confirm_seconds:
            self._alert_call_fired[alert_type] = True
            self.statusBar().showMessage(
                f"🔔 Threat confirmed — dispatching alerts for "
                f"{alert_type.replace('_', ' ').title()}", 5000
            )
            return True
        return False

    def _fire_external_alerts(self, alert_type, confidence, frame):
        def _bg():
            screenshot_path = ""
            try:
                screenshot_path = self._alert_manager._save_screenshot(
                    frame, alert_type, self._camera_name
                ) or ""
            except Exception:
                pass
            if self.auth:
                self.auth.report_alert(alert_type, confidence,
                                       self._camera_name, screenshot_path)

            if self._firebase_notifier and self.auth and self.auth.uid:
                self._firebase_notifier.send_alert(
                    uid=self.auth.uid, alert_type=alert_type,
                    confidence=confidence, camera_name=self._camera_name
                )
        threading.Thread(target=_bg, daemon=True).start()

    @Slot(bool, float, tuple)
    def _on_stream_status(self, connected, fps, resolution):
        self.video_widget.set_status(connected, self._camera_name, fps, resolution)
        self.sb_camera.setText(
            f"Camera: {self._camera_name} ({resolution[0]}x{resolution[1]})"
        )

    def _on_module_toggle(self, module_id, enabled):
        if self.auth and enabled:
            if not self.auth.is_subscription_active:
                QMessageBox.warning(self, "Subscription Expired",
                                    "Renew your subscription to use detection modules.")
                return
        if self._engine:

            self._engine.set_module_enabled(module_id, enabled)

    def _stop_alarm(self):
        if self._alert_manager:
            self._alert_manager.stop_alarm()
            self.video_widget.trigger_alert(False)
            self.statusBar().showMessage("🔕 Alarm silenced", 3000)

    def _take_snapshot(self):
        if self._stream and self._stream.is_connected:
            frame = self._stream.get_latest_frame()
            if frame is not None:
                self._alert_manager._save_screenshot(frame, "snapshot", self._camera_name)
                self.statusBar().showMessage("Snapshot saved!", 3000)

    def _update_status(self, text, color):
        for w in [self.status_dot, self.status_text]:
            w.setStyleSheet(f"color:{color}; font-size:10px; background:transparent;")
        self.status_text.setText(text)

    def _logout(self):
        if QMessageBox.question(self, "Sign Out", "Sign out of AlertEye?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._stop_stream()
            if self.auth:
                self.auth.logout()
            self.close()
            import subprocess, sys
            subprocess.Popen([sys.executable] + sys.argv)

    def _check_first_run(self):
        from utils.model_downloader import MODEL_REGISTRY, model_exists
        missing = any(
            not model_exists(info["filename"])
            for name, info in MODEL_REGISTRY.items()
            if name in ["general_yolov8n"]
        )
        if missing:
            from ui.model_setup_dialog import ModelSetupDialog
            ModelSetupDialog(self).exec()

    def closeEvent(self, event):
        self._stop_stream()
        if self._engine:       self._engine.shutdown()
        if self._alert_manager: self._alert_manager.cleanup()
        logger.info("AlertEye shutting down.")
        event.accept()
