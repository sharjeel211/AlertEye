"""
Settings Panel - Configurable parameters for detection, cameras, storage, alerts
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QGroupBox, QComboBox, QLineEdit, QPushButton, QSpinBox,
    QDoubleSpinBox, QFileDialog, QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal

class SettingsWidget(QWidget):
    """
    Settings panel with scrollable sections for all configurable options.
    Emits signals when settings change.
    """

    setting_changed = Signal(str, object)
    save_requested = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("topbar")
        header.setFixedHeight(40)
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(16, 0, 16, 0)
        title = QLabel("SYSTEM SETTINGS")
        title.setObjectName("section_title")
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("btn_primary")
        save_btn.setFixedSize(110, 26)
        save_btn.clicked.connect(self._save)
        hlayout.addWidget(title)
        hlayout.addStretch()
        hlayout.addWidget(save_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_camera_section())
        content_layout.addWidget(self._build_detection_section())
        content_layout.addWidget(self._build_alert_section())
        content_layout.addWidget(self._build_storage_section())
        content_layout.addWidget(self._build_display_section())
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(header)
        main_layout.addWidget(scroll, 1)

    def _build_camera_section(self) -> QGroupBox:
        box = self._group("CAMERA SOURCE")
        layout = QGridLayout(box)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Default Source:"), 0, 0)
        self.cam_source = QComboBox()
        self.cam_source.addItem("Webcam (index 0)", "0")
        self.cam_source.addItem("Webcam (index 1)", "1")
        self.cam_source.addItem("RTSP Stream", "rtsp")
        self.cam_source.addItem("Video File", "file")
        layout.addWidget(self.cam_source, 0, 1)

        layout.addWidget(QLabel("RTSP / IP URL:"), 1, 0)
        self.rtsp_url = QLineEdit()
        self.rtsp_url.setPlaceholderText("rtsp://user:pass@192.168.1.100:554/stream")
        layout.addWidget(self.rtsp_url, 1, 1)

        layout.addWidget(QLabel("Resolution:"), 2, 0)
        res_box = QComboBox()
        res_box.addItems(["1920×1080", "1280×720", "960×540", "640×480"])
        res_box.setCurrentIndex(1)
        self.cam_resolution = res_box
        layout.addWidget(res_box, 2, 1)

        layout.addWidget(QLabel("Target FPS:"), 3, 0)
        self.cam_fps = QSpinBox()
        self.cam_fps.setRange(1, 60)
        self.cam_fps.setValue(30)
        layout.addWidget(self.cam_fps, 3, 1)

        return box

    def _build_detection_section(self) -> QGroupBox:
        box = self._group("DETECTION ENGINE")
        layout = QGridLayout(box)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Global Confidence:"), 0, 0)
        conf_row = QHBoxLayout()
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(10, 95)
        self.conf_slider.setValue(45)
        self.conf_slider.setTickInterval(5)
        self.conf_label = QLabel("0.45")
        self.conf_label.setFixedWidth(35)
        self.conf_label.setStyleSheet("color: #1d4ed8; font-family: monospace;")
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f"{v/100:.2f}")
        )
        conf_row.addWidget(self.conf_slider)
        conf_row.addWidget(self.conf_label)
        conf_w = QWidget()
        conf_w.setLayout(conf_row)
        layout.addWidget(conf_w, 0, 1)

        layout.addWidget(QLabel("Frame Skip:"), 1, 0)
        self.frame_skip = QSpinBox()
        self.frame_skip.setRange(1, 10)
        self.frame_skip.setValue(2)
        self.frame_skip.setToolTip("Process every Nth frame (1=every frame, 2=every other)")
        layout.addWidget(self.frame_skip, 1, 1)

        layout.addWidget(QLabel("Device:"), 2, 0)
        self.device_combo = QComboBox()
        self.device_combo.addItem("Auto (GPU if available)", "auto")
        self.device_combo.addItem("CPU", "cpu")
        self.device_combo.addItem("GPU (cuda:0)", "cuda:0")
        layout.addWidget(self.device_combo, 2, 1)

        layout.addWidget(QLabel("Max Detections:"), 3, 0)
        self.max_det = QSpinBox()
        self.max_det.setRange(1, 100)
        self.max_det.setValue(50)
        layout.addWidget(self.max_det, 3, 1)

        return box

    def _build_alert_section(self) -> QGroupBox:
        box = self._group("ALERTS & NOTIFICATIONS")
        layout = QGridLayout(box)
        layout.setSpacing(10)

        self.alert_sound = QCheckBox("Enable Alert Sound")
        self.alert_sound.setChecked(True)
        layout.addWidget(self.alert_sound, 0, 0, 1, 2)

        self.alert_screenshot = QCheckBox("Screenshot on Detection")
        self.alert_screenshot.setChecked(True)
        layout.addWidget(self.alert_screenshot, 1, 0, 1, 2)

        self.alert_record = QCheckBox("Record Video Clip on Alert")
        self.alert_record.setChecked(True)
        layout.addWidget(self.alert_record, 2, 0, 1, 2)

        layout.addWidget(QLabel("Alert Cooldown (s):"), 3, 0)
        self.alert_cooldown = QSpinBox()
        self.alert_cooldown.setRange(1, 120)
        self.alert_cooldown.setValue(10)
        layout.addWidget(self.alert_cooldown, 3, 1)

        layout.addWidget(QLabel("Clip Duration (s):"), 4, 0)
        self.clip_duration = QSpinBox()
        self.clip_duration.setRange(5, 60)
        self.clip_duration.setValue(15)
        layout.addWidget(self.clip_duration, 4, 1)

        return box

    def _build_storage_section(self) -> QGroupBox:
        box = self._group("STORAGE")
        layout = QGridLayout(box)
        layout.setSpacing(10)

        for row, (lbl, attr, default) in enumerate([
            ("Screenshots Path:", "path_screenshots", "screenshots"),
            ("Recordings Path:",  "path_recordings",  "recordings"),
            ("Logs Path:",        "path_logs",         "logs"),
        ]):
            layout.addWidget(QLabel(lbl), row, 0)
            edit = QLineEdit(default)
            btn  = QPushButton("Browse")
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda _, e=edit: self._browse_dir(e))
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.addWidget(edit)
            row_l.addWidget(btn)
            setattr(self, attr, edit)
            layout.addWidget(row_w, row, 1)

        layout.addWidget(QLabel("Max Storage (GB):"), 3, 0)
        self.max_storage = QSpinBox()
        self.max_storage.setRange(1, 1000)
        self.max_storage.setValue(10)
        layout.addWidget(self.max_storage, 3, 1)

        self.auto_cleanup = QCheckBox("Auto-cleanup when storage full")
        self.auto_cleanup.setChecked(True)
        layout.addWidget(self.auto_cleanup, 4, 0, 1, 2)

        return box

    def _build_display_section(self) -> QGroupBox:
        box = self._group("DISPLAY OPTIONS")
        layout = QGridLayout(box)
        layout.setSpacing(10)

        self.show_fps = QCheckBox("Show FPS Counter")
        self.show_fps.setChecked(True)
        layout.addWidget(self.show_fps, 0, 0)

        self.show_confidence = QCheckBox("Show Confidence Scores")
        self.show_confidence.setChecked(True)
        layout.addWidget(self.show_confidence, 0, 1)

        self.show_labels = QCheckBox("Show Detection Labels")
        self.show_labels.setChecked(True)
        layout.addWidget(self.show_labels, 1, 0)

        self.show_bbox = QCheckBox("Show Bounding Boxes")
        self.show_bbox.setChecked(True)
        layout.addWidget(self.show_bbox, 1, 1)

        return box

    def _group(self, title: str) -> QGroupBox:

        return QGroupBox(title)

    def _browse_dir(self, line_edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        if d:
            line_edit.setText(d)

    def _load_values(self):
        """Load current config values into widgets."""
        self.conf_slider.setValue(
            int(self.config.get("detection", "confidence_threshold", default=0.45) * 100)
        )
        self.frame_skip.setValue(
            self.config.get("detection", "frame_skip", default=2)
        )
        self.alert_sound.setChecked(
            self.config.get("alerts", "sound_enabled", default=True)
        )
        self.alert_cooldown.setValue(
            self.config.get("alerts", "alert_cooldown_seconds", default=10)
        )
        self.clip_duration.setValue(
            self.config.get("alerts", "record_duration_seconds", default=15)
        )

    def _save(self):
        """Gather all values and save to config."""
        self.config.set(self.conf_slider.value() / 100,
                        "detection", "confidence_threshold")
        self.config.set(self.frame_skip.value(), "detection", "frame_skip")
        self.config.set(self.device_combo.currentData(), "detection", "device")
        self.config.set(self.alert_sound.isChecked(), "alerts", "sound_enabled")
        self.config.set(self.alert_screenshot.isChecked(), "alerts", "screenshot_on_alert")
        self.config.set(self.alert_record.isChecked(), "alerts", "record_on_alert")
        self.config.set(self.alert_cooldown.value(), "alerts", "alert_cooldown_seconds")
        self.config.set(self.clip_duration.value(), "alerts", "record_duration_seconds")
        self.config.set(self.path_screenshots.text(), "storage", "screenshots_path")
        self.config.set(self.path_recordings.text(), "storage", "recordings_path")
        self.save_requested.emit()
