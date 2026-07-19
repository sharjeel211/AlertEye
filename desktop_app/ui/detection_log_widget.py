"""
Detection Log Panel - Real-time alert log and detection history display
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon

THREAT_CONFIG = {
    "CRITICAL": {"color": "#ff2244", "bg": "#120408", "icon": "🔴", "prefix": "CRITICAL"},
    "HIGH":     {"color": "#ff8800", "bg": "#100c02", "icon": "🟠", "prefix": "HIGH"},
    "MEDIUM":   {"color": "#ffc000", "bg": "#0f0e02", "icon": "🟡", "prefix": "WARN"},
    "LOW":      {"color": "#3b82f6", "bg": "#0c1830", "icon": "🟢", "prefix": "INFO"},
    "INFO":     {"color": "#4a9fd4", "bg": "#020c14", "icon": "🔵", "prefix": "INFO"},
}

MODULE_ICONS = {
    "weapon_detection":     "⚠",
    "fire_smoke_detection": "🔥",
    "accident_detection":   "💥",
}

class AlertLogWidget(QWidget):
    """
    Real-time detection alert log panel.
    Shows scrolling list of detection events with color coding.
    """

    alert_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("alert_panel")
        self._entries = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("alert_header")
        header.setFixedHeight(32)
        hlayout = QHBoxLayout(header)
        hlayout.setContentsMargins(12, 0, 8, 0)

        title = QLabel("DETECTION LOG")
        title.setObjectName("alert_header")
        title.setStyleSheet(
            "font-size: 10px; font-weight: 700; letter-spacing: 2.5px; "
            "color: #2a4060; background: transparent;"
        )

        self.lbl_count = QLabel("0 events")
        self.lbl_count.setStyleSheet("color: #1e3050; font-size: 10px; font-family: 'Courier New';")

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedSize(50, 22)
        btn_clear.setStyleSheet(
            "QPushButton { background: transparent; color: #2a4060; border: none; "
            "font-size: 10px; } QPushButton:hover { color: #c8d0dc; }"
        )
        btn_clear.clicked.connect(self.clear_log)

        hlayout.addWidget(title)
        hlayout.addStretch()
        hlayout.addWidget(self.lbl_count)
        hlayout.addWidget(btn_clear)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("alert_list")
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setSpacing(1)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(header)
        layout.addWidget(self.list_widget, 1)

    def add_detection(self, module_name: str, label: str,
                      confidence: float, threat_level: str = "HIGH",
                      camera_id: str = "CAM-01"):
        """Add a new detection entry to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        cfg = THREAT_CONFIG.get(threat_level, THREAT_CONFIG["INFO"])
        icon = MODULE_ICONS.get(module_name, "◉")

        entry = {
            "time": timestamp,
            "module": module_name,
            "label": label,
            "confidence": confidence,
            "threat_level": threat_level,
            "camera": camera_id,
            "icon": icon
        }
        self._entries.append(entry)

        display_text = (
            f"{cfg['icon']} {timestamp}  "
            f"[{camera_id}]  "
            f"{label}  "
            f"{confidence:.0%}"
        )

        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, entry)
        item.setForeground(QColor(cfg["color"]))
        item.setBackground(QColor(cfg["bg"]))
        item.setFont(QFont("Courier New", 10))

        self.list_widget.insertItem(0, item)

        while self.list_widget.count() > 500:
            self.list_widget.takeItem(self.list_widget.count() - 1)

        self.lbl_count.setText(f"{len(self._entries)} events")

    def clear_log(self):
        self.list_widget.clear()
        self._entries.clear()
        self.lbl_count.setText("0 events")

    def _on_item_clicked(self, item: QListWidgetItem):
        entry = item.data(Qt.UserRole)
        if entry:
            self.alert_selected.emit(entry)

class ModuleStatusPanel(QWidget):
    """
    Shows status cards for each detection module.
    Allows enabling/disabling and shows real-time activity.
    """

    module_toggled = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = {}
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(6)

        title = QLabel("DETECTION MODULES")
        title.setObjectName("section_title")
        title.setStyleSheet(
            "color: #2a4060; font-size: 9px; font-weight: 700; "
            "letter-spacing: 2px; padding: 4px 0;"
        )
        self.layout.addWidget(title)

        modules = [
            ("weapon_detection",    "⚠  Weapon Detector",   True),
            ("fire_smoke_detection","🔥  Fire & Smoke",       True),
            ("accident_detection",  "💥  Accident/Collision", True),
        ]

        for module_id, display_name, enabled in modules:
            card = self._make_module_card(module_id, display_name, enabled)
            self._cards[module_id] = card
            self.layout.addWidget(card)

        self.layout.addStretch()

    def _make_module_card(self, module_id: str, name: str, enabled: bool) -> QWidget:
        card = QFrame()
        card.setObjectName("module_card")
        card.setFixedHeight(48)
        card.setProperty("active", enabled)
        card.setStyleSheet(
            f"QFrame#module_card {{ background: {'#10203c' if enabled else '#090c16'}; "
            f"border: 1px solid {'#3b82f6' if enabled else '#121e30'}; border-radius: 5px; }}"
        )

        hlayout = QHBoxLayout(card)
        hlayout.setContentsMargins(10, 6, 10, 6)

        lbl_name = QLabel(name)
        lbl_name.setObjectName("module_name")
        lbl_name.setStyleSheet("color: #6080a0; font-size: 11px; font-weight: 500;")

        lbl_status = QLabel("ACTIVE" if enabled else "DISABLED")
        lbl_status.setObjectName("module_status")
        lbl_status.setStyleSheet(
            f"color: {'#3b82f6' if enabled else '#2a4060'}; "
            "font-size: 9px; letter-spacing: 1px;"
        )

        from PySide6.QtWidgets import QCheckBox
        toggle = QCheckBox()
        toggle.setChecked(enabled)
        toggle.setStyleSheet(
            "QCheckBox::indicator { width: 28px; height: 16px; border-radius: 8px; "
            "background: #101828; border: 1px solid #1a2e48; } "
            "QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }"
        )
        toggle.stateChanged.connect(
            lambda state, mid=module_id: self._on_toggle(mid, bool(state))
        )

        col_layout = QVBoxLayout()
        col_layout.setSpacing(2)
        col_layout.addWidget(lbl_name)
        col_layout.addWidget(lbl_status)

        hlayout.addLayout(col_layout)
        hlayout.addStretch()
        hlayout.addWidget(toggle)

        card._status_label = lbl_status
        card._toggle = toggle
        return card

    def _on_toggle(self, module_id: str, enabled: bool):
        card = self._cards.get(module_id)
        if card:
            card._status_label.setText("ACTIVE" if enabled else "DISABLED")
            card._status_label.setStyleSheet(
                f"color: {'#3b82f6' if enabled else '#2a4060'}; "
                "font-size: 9px; letter-spacing: 1px;"
            )
            card.setStyleSheet(
                f"QFrame#module_card {{ background: {'#10203c' if enabled else '#090c16'}; "
                f"border: 1px solid {'#3b82f6' if enabled else '#121e30'}; border-radius: 5px; }}"
            )
        self.module_toggled.emit(module_id, enabled)

    def set_module_locked(self, module_id: str, locked: bool):
        """Lock or unlock a module based on subscription."""

        full_id = module_id if module_id in self._cards else f"{module_id}_detection"
        card = self._cards.get(full_id)
        if not card:
            return
        card._toggle.setEnabled(not locked)
        if locked:
            card._toggle.setChecked(False)
            card._status_label.setText("🔒 LOCKED")
            card._status_label.setStyleSheet("color: #4a6080; font-size: 9px; letter-spacing: 1px;")
            card.setStyleSheet(
                "QFrame#module_card { background: #090c16; "
                "border: 1px solid #162030; border-radius: 5px; opacity: 0.5; }"
            )

    def set_module_alert(self, module_id: str, alert: bool):
        """Flash a module card when detection occurs."""
        card = self._cards.get(module_id)
        if card:
            if alert:
                card._status_label.setText("⚠ DETECTED")
                card._status_label.setStyleSheet("color: #ff2244; font-size: 9px; letter-spacing: 1px;")
            elif card._toggle.isChecked():
                card._status_label.setText("ACTIVE")
                card._status_label.setStyleSheet("color: #3b82f6; font-size: 9px; letter-spacing: 1px;")
