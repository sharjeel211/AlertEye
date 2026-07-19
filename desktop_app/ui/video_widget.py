"""
Video Feed Widget - Displays live camera feed with detection overlays
Handles OpenCV BGR → Qt RGB conversion efficiently
"""

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen, QFont

class VideoDisplay(QLabel):
    """
    High-performance video frame display label.
    Accepts numpy BGR frames and renders them scaled to fit.
    """

    clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: #020304; border: none;")
        self._current_frame: np.ndarray = None
        self._placeholder = True
        self._draw_placeholder()

    def _draw_placeholder(self):
        """Draw a stylised 'no signal' placeholder."""
        w, h = 640, 360
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (8, 12, 16)

        for i in range(0, w, 40):
            for j in range(0, h, 40):
                cv2.circle(img, (i, j), 1, (18, 28, 38), -1)

        cx, cy = w // 2, h // 2
        cv2.circle(img, (cx, cy), 72, (15, 35, 25), 1)
        cv2.circle(img, (cx, cy), 58, (10, 25, 18), 1)

        cv2.rectangle(img, (cx - 28, cy - 18), (cx + 28, cy + 18), (0, 120, 70), 2)

        cv2.circle(img, (cx, cy), 10, (0, 140, 80), 2)
        cv2.circle(img, (cx, cy), 4,  (0, 100, 60), -1)

        cv2.rectangle(img, (cx + 22, cy - 10), (cx + 32, cy - 2), (0, 100, 60), -1)

        size, gap = 16, 3
        color_corner = (0, 90, 55)
        for ox, oy, sx, sy in [(cx-72, cy-40, 1, 1), (cx+72, cy-40, -1, 1),
                                (cx-72, cy+40, 1, -1), (cx+72, cy+40, -1, -1)]:
            cv2.line(img, (ox, oy), (ox + sx*size, oy), color_corner, 1)
            cv2.line(img, (ox, oy), (ox, oy + sy*size), color_corner, 1)

        text = "NO SIGNAL"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, _), _ = cv2.getTextSize(text, font, 0.65, 1)
        cv2.putText(img, text, ((w - tw) // 2, cy + 62),
                    font, 0.65, (0, 160, 90), 1, cv2.LINE_AA)

        sub = "Select a source and press START"
        (sw, _), _ = cv2.getTextSize(sub, font, 0.38, 1)
        cv2.putText(img, sub, ((w - sw) // 2, cy + 86),
                    font, 0.38, (0, 80, 50), 1, cv2.LINE_AA)

        self.set_frame(img)

    def set_frame(self, frame: np.ndarray):
        """Display a BGR numpy frame."""
        if frame is None:
            return
        self._current_frame = frame
        self._placeholder = False
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)

        scaled = pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)

    def set_offline(self):
        """Show offline/disconnected state."""
        h, w = 360, 640
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (8, 8, 12)
        text = "CAMERA OFFLINE"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(img, text, ((w - tw) // 2, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 20, 20), 2)
        self.set_frame(img)

    def mousePressEvent(self, event):
        if not self.pixmap() or self._current_frame is None:
            return

        lw, lh = self.width(), self.height()
        pw, ph = self.pixmap().width(), self.pixmap().height()
        fh, fw = self._current_frame.shape[:2]
        ox = (lw - pw) // 2
        oy = (lh - ph) // 2
        px = int(event.position().x()) - ox
        py = int(event.position().y()) - oy
        if 0 <= px <= pw and 0 <= py <= ph:
            fx = int(px * fw / pw)
            fy = int(py * fh / ph)
            self.clicked.emit(fx, fy)

class CameraInfoOverlay(QWidget):
    """Transparent overlay showing camera info and alert status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._camera_name = "CAM-01"
        self._fps = 0.0
        self._alert_active = False
        self._resolution = (0, 0)

    def update_info(self, camera_name: str, fps: float,
                    alert: bool, resolution: tuple = (0, 0)):
        self._camera_name = camera_name
        self._fps = fps
        self._alert_active = alert
        self._resolution = resolution
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()

            font = QFont("Courier New", 9)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(0, 255, 136))
            cam_text = f"● {self._camera_name}"
            p.drawText(10, 20, cam_text)

            fps_text = f"FPS: {self._fps:.0f}"
            p.setPen(QColor(90, 100, 120))
            fm = p.fontMetrics()
            p.drawText(w - fm.horizontalAdvance(fps_text) - 10, 20, fps_text)

            if self._resolution[0] > 0:
                res_text = f"{self._resolution[0]}×{self._resolution[1]}"
                p.setPen(QColor(60, 70, 90))
                p.drawText(w - fm.horizontalAdvance(res_text) - 10, 36, res_text)

            if self._alert_active:
                pen = QPen(QColor(255, 34, 68), 4)
                p.setPen(pen)
                p.drawRect(2, 2, w - 4, h - 4)

                font2 = QFont("Segoe UI", 9)
                font2.setBold(True)
                p.setFont(font2)
                p.setPen(QColor(255, 34, 68))
                p.drawText(10, h - 15, "⚠ ALERT ACTIVE")
        finally:
            p.end()

class VideoFeedWidget(QWidget):
    """
    Complete video feed widget with toolbar, display, and overlay.
    """

    source_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("video_panel")
        self._setup_ui()
        self._alert_blink_state = False
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._blink_alert)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget()
        toolbar.setObjectName("video_toolbar")
        toolbar.setFixedHeight(36)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        tb_layout.setSpacing(8)

        self.camera_combo = QComboBox()
        self.camera_combo.setObjectName("camera_selector")
        self.camera_combo.addItem("📷 Webcam (0)", "0")
        self.camera_combo.addItem("📡 IP Camera / RTSP", "rtsp://")
        self.camera_combo.addItem("🎬 Video File...", "file")
        self.camera_combo.setFixedWidth(180)
        self.camera_combo.currentIndexChanged.connect(self._on_source_change)

        self.btn_start = QPushButton("▶  START")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setFixedHeight(26)
        self.btn_start.setFixedWidth(90)

        self.btn_stop = QPushButton("■  STOP")
        self.btn_stop.setFixedHeight(26)
        self.btn_stop.setFixedWidth(80)

        self.btn_snapshot = QPushButton("📸")
        self.btn_snapshot.setFixedSize(26, 26)
        self.btn_snapshot.setToolTip("Take Snapshot")

        self.btn_stop_alarm = QPushButton("🔕  STOP ALARM")
        self.btn_stop_alarm.setFixedHeight(26)
        self.btn_stop_alarm.setToolTip("Silence the alarm")
        self.btn_stop_alarm.setStyleSheet(
            "background:#7f1d1d; color:#fecaca; font-weight:600;"
        )

        self.lbl_status = QLabel("● OFFLINE")
        self.lbl_status.setStyleSheet("color: #1e3050; font-size: 10px; font-family: 'Courier New'; letter-spacing: 1px;")

        tb_layout.addWidget(QLabel("SOURCE:"))
        tb_layout.addWidget(self.camera_combo)
        tb_layout.addWidget(self.btn_start)
        tb_layout.addWidget(self.btn_stop)
        tb_layout.addWidget(self.btn_snapshot)
        tb_layout.addWidget(self.btn_stop_alarm)
        tb_layout.addStretch()
        tb_layout.addWidget(self.lbl_status)

        self.display = VideoDisplay()
        self.overlay = CameraInfoOverlay(self.display)
        self.overlay.resize(self.display.size())

        layout.addWidget(toolbar)
        layout.addWidget(self.display, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "overlay"):
            self.overlay.resize(self.display.size())

    def update_frame(self, frame: np.ndarray):
        """Push new frame to display."""
        self.display.set_frame(frame)

    def set_status(self, online: bool, camera_name: str = "CAM-01",
                   fps: float = 0.0, resolution: tuple = (0, 0)):
        if online:
            self.lbl_status.setText(f"● LIVE  {fps:.0f} fps")
            self.lbl_status.setStyleSheet(
                "color: #3b82f6; font-size: 10px; font-family: 'Courier New'; letter-spacing: 1px;"
            )
        else:
            self.lbl_status.setText("● OFFLINE")
            self.lbl_status.setStyleSheet(
                "color: #1e3050; font-size: 10px; font-family: 'Courier New'; letter-spacing: 1px;"
            )

    def trigger_alert(self, active: bool):
        if active and not self._blink_timer.isActive():
            self._blink_timer.start(500)
        elif not active:
            self._blink_timer.stop()
            self.overlay.update_info("", 0, False)

    def _blink_alert(self):
        self._alert_blink_state = not self._alert_blink_state
        self.overlay.update_info(
            self.overlay._camera_name,
            self.overlay._fps,
            self._alert_blink_state
        )

    def update_overlay(self, camera_name: str, fps: float,
                       alert: bool, resolution: tuple = (0, 0)):
        self.overlay.update_info(camera_name, fps, alert, resolution)

    def set_offline(self):
        self.display.set_offline()
        self.trigger_alert(False)
        self.set_status(False)

    def _on_source_change(self, idx):
        data = self.camera_combo.itemData(idx)
        if data:
            self.source_changed.emit(str(data))

    def get_selected_source(self) -> str:
        return self.camera_combo.currentData() or "0"
