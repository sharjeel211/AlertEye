"""
AlertEye — Premium Dark Surveillance Dashboard Stylesheet
"""

MAIN_STYLESHEET = """
/* ─── Global ──────────────────────────────────────────── */
* {
    font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #0a0f1c;
    color: #d6e1f0;
}

QWidget {
    background-color: transparent;
    color: #d6e1f0;
}

/* ─── Scrollbars ──────────────────────────────────────── */
QScrollBar:vertical {
    background: #0c1322;
    width: 6px;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #24324d;
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #0c1322;
    height: 6px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #24324d;
    border-radius: 3px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ─── Top Bar ─────────────────────────────────────────── */
#topbar {
    background-color: #0b1322;
    border-bottom: 1px solid #1b2740;
    min-height: 56px;
    max-height: 56px;
}

#topbar_logo {
    color: #eaf1fb;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 2px;
    background: transparent;
}

#topbar_user {
    font-size: 12px;
    background: transparent;
    color: #6b7e9c;
}

/* ─── Navigation Sidebar ─────────────────────────────── */
#sidebar {
    background-color: #0b1120;
    border-right: 1px solid #182238;
    min-width: 232px;
    max-width: 232px;
}

QPushButton#nav_btn {
    background: transparent;
    color: #6b7e9c;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 13px 22px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.3px;
    border-radius: 0;
}
QPushButton#nav_btn:hover {
    background-color: #121d33;
    color: #bcd0ee;
    border-left-color: #2a3c5c;
}
QPushButton#nav_btn[active="true"] {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(37,99,235,0.22), stop:1 rgba(37,99,235,0.02));
    color: #5b9bff;
    border-left: 3px solid #2563eb;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* ─── Status Panel (sidebar footer) ──────────────────── */
#status_panel {
    background: #0a101e;
    border-top: 1px solid #182238;
    padding: 10px 14px;
}

#status_dot_label {
    background: transparent;
    font-size: 11px;
}

#status_text_label {
    background: transparent;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}

/* ─── Main Content Area ──────────────────────────────── */
#main_content {
    background: #0d1424;
}

QStackedWidget {
    background: #0d1424;
}

/* ─── Video Feed Panel ───────────────────────────────── */
#video_panel {
    background: #060a14;
    border: 1px solid #1d2941;
    border-radius: 10px;
}

#video_toolbar {
    background: #0c1322;
    border-bottom: 1px solid #1b2740;
    border-radius: 10px 10px 0 0;
    padding: 2px 8px;
    min-height: 38px;
    max-height: 38px;
}

#camera_selector {
    background: #111a2e;
    color: #bcd0ee;
    border: 1px solid #233149;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
}
#camera_selector:hover {
    border-color: #3b82f6;
}
#camera_selector QAbstractItemView {
    background: #111a2e;
    border: 1px solid #233149;
    color: #bcd0ee;
    selection-background-color: #1a2f56;
}

/* ─── Alert / Detection Log ──────────────────────────── */
#alert_panel {
    background: #0c1322;
    border: 1px solid #182238;
    border-radius: 10px;
}

#alert_header {
    background: #0e1628;
    border-bottom: 1px solid #182238;
    padding: 9px 14px;
    font-size: 10px;
    letter-spacing: 2.5px;
    color: #5b9bff;
    font-weight: 700;
    border-radius: 10px 10px 0 0;
}

QListWidget#alert_list {
    background: transparent;
    border: none;
    color: #d6e1f0;
    font-size: 11px;
}
QListWidget#alert_list::item {
    padding: 7px 14px;
    border-bottom: 1px solid #131c30;
}
QListWidget#alert_list::item:hover {
    background: #131f38;
}
QListWidget#alert_list::item:selected {
    background: #16294d;
    color: #5b9bff;
}

/* ─── Detection Module Cards ─────────────────────────── */
#module_card {
    background: #111a2e;
    border: 1px solid #1d2941;
    border-radius: 8px;
}
#module_card:hover {
    border-color: #2a3c5c;
    background: #14203a;
}
#module_card[active="true"] {
    border-color: #2563eb;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(37,99,235,0.16), stop:1 rgba(37,99,235,0.03));
}

#module_name {
    color: #9fb3d4;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
#module_status {
    color: #4a5e80;
    font-size: 9px;
    letter-spacing: 1px;
}
#module_status[state="active"] { color: #3b82f6; }
#module_status[state="alert"]  { color: #ef4444; }

/* ─── Toggle Switch ──────────────────────────────────── */
QCheckBox {
    color: #9fb3d4;
    font-size: 11px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 32px;
    height: 17px;
    border-radius: 8px;
    background: #1a2742;
    border: 1px solid #283c5e;
}
QCheckBox::indicator:checked {
    background: #2563eb;
    border-color: #3b82f6;
}
QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

/* ─── Sliders ─────────────────────────────────────────── */
QSlider::groove:horizontal {
    background: #1a2742;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3b82f6;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 2px solid #0a0f1c;
}
QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 2px;
}

/* ─── Buttons ─────────────────────────────────────────── */
QPushButton {
    background: #15203a;
    color: #aebfdc;
    border: 1px solid #233149;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 500;
}
QPushButton:hover {
    background: #1b2a49;
    border-color: #2f436a;
    color: #dbe7f8;
}
QPushButton:pressed {
    background: #121b30;
    border-color: #3b82f6;
}
QPushButton:disabled {
    background: #0e1628;
    color: #3a4d6e;
    border-color: #182238;
}

QPushButton#btn_primary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
    border: none;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.5px;
}
QPushButton#btn_primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4f92ff, stop:1 #2f6ef0);
}
QPushButton#btn_primary:pressed {
    background: #1d4ed8;
}

QPushButton#btn_danger {
    background: #2a0e14;
    color: #ff5a72;
    border: 1px solid #51202c;
}
QPushButton#btn_danger:hover {
    background: #38131c;
    border-color: #ef4444;
}

QPushButton#btn_danger_sm {
    background: transparent;
    color: #ff5a72;
    border: 1px solid #51202c;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton#btn_danger_sm:hover {
    background: #2a0e14;
    border-color: #ef4444;
}

QPushButton#btn_icon {
    background: transparent;
    border: 1px solid #1d2941;
    border-radius: 7px;
    font-size: 15px;
    padding: 4px;
    color: #6b7e9c;
}
QPushButton#btn_icon:hover {
    background: #131f38;
    border-color: #3b82f6;
    color: #5b9bff;
}

/* ─── Group Boxes ─────────────────────────────────────── */
QGroupBox {
    border: 1px solid #1d2941;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    color: #6b7e9c;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #5b9bff;
    background: #0a0f1c;
}

/* ─── Labels ─────────────────────────────────────────── */
QLabel#section_title {
    color: #6b7e9c;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2.5px;
    background: transparent;
}

QLabel#metric_value {
    color: #5b9bff;
    font-size: 22px;
    font-weight: 700;
    font-family: "Segoe UI", "Courier New", monospace;
    background: transparent;
}
QLabel#metric_label {
    color: #4a5e80;
    font-size: 9px;
    letter-spacing: 1.5px;
    background: transparent;
}
QLabel#about_text {
    background: transparent;
    color: #d6e1f0;
    line-height: 1.6;
}
QLabel#sub_info_box {
    background: #111d36;
    border: 1px solid #233e6a;
    border-radius: 10px;
}

QLabel#alert_critical { color: #ef4444; font-weight: 700; }
QLabel#alert_high     { color: #f97316; }
QLabel#alert_medium   { color: #fbbf24; }

/* ─── Tab Widget ─────────────────────────────────────── */
QTabWidget::pane {
    background: #0d1424;
    border: 1px solid #1d2941;
    border-top: none;
    border-radius: 0 0 8px 8px;
}
QTabBar::tab {
    background: #0b1120;
    color: #6b7e9c;
    padding: 8px 20px;
    border: 1px solid #1d2941;
    border-bottom: none;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
}
QTabBar::tab:selected {
    background: #0d1424;
    color: #5b9bff;
    border-bottom: 2px solid #2563eb;
}
QTabBar::tab:hover:!selected {
    background: #121d33;
    color: #9fb3d4;
}

/* ─── ComboBox ────────────────────────────────────────── */
QComboBox {
    background: #111a2e;
    color: #bcd0ee;
    border: 1px solid #233149;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 11px;
    min-width: 120px;
}
QComboBox:hover { border-color: #3b82f6; }
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background: #111a2e;
    border: 1px solid #233149;
    color: #bcd0ee;
    selection-background-color: #16294d;
    selection-color: #5b9bff;
    outline: none;
}

/* ─── LineEdit ────────────────────────────────────────── */
QLineEdit {
    background: #111a2e;
    color: #bcd0ee;
    border: 1px solid #233149;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}
QLineEdit:focus { border-color: #3b82f6; }

/* ─── SpinBox ─────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {
    background: #111a2e;
    color: #bcd0ee;
    border: 1px solid #233149;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 11px;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #3b82f6; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: #1a2742;
    border: none;
    width: 16px;
}

/* ─── Status Bar ──────────────────────────────────────── */
QStatusBar {
    background: #0a101e;
    border-top: 1px solid #182238;
    color: #6b7e9c;
    font-size: 10px;
    letter-spacing: 0.5px;
}
QStatusBar::item { border: none; }

/* ─── Frame / Separator ───────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #182238;
    background: #182238;
    border: none;
}

/* ─── Tooltip ─────────────────────────────────────────── */
QToolTip {
    background: #131f38;
    color: #d6e1f0;
    border: 1px solid #233149;
    padding: 5px 9px;
    font-size: 11px;
    border-radius: 6px;
}

/* ─── ProgressBar ─────────────────────────────────────── */
QProgressBar {
    background: #1a2742;
    border: none;
    border-radius: 3px;
    height: 6px;
    color: transparent;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #3b82f6);
    border-radius: 3px;
}

/* ─── MessageBox ──────────────────────────────────────── */
QMessageBox {
    background: #0d1424;
}
QMessageBox QLabel {
    color: #d6e1f0;
    background: transparent;
}
QMessageBox QPushButton {
    min-width: 70px;
}

/* ─── InputDialog ─────────────────────────────────────── */
QInputDialog QLabel {
    color: #d6e1f0;
    background: transparent;
}
"""

COLORS = {
    "bg_deep":       "#0a0f1c",
    "bg_panel":      "#0d1424",
    "bg_dark":       "#0b1322",
    "bg_card":       "#111a2e",
    "border":        "#1d2941",
    "border_hover":  "#2f436a",
    "accent":        "#3b82f6",
    "accent_dim":    "#2563eb",
    "brand_red":     "#e11d2b",
    "text_primary":  "#d6e1f0",
    "text_muted":    "#6b7e9c",
    "text_dim":      "#4a5e80",
    "alert_critical":"#ef4444",
    "alert_high":    "#f97316",
    "alert_medium":  "#fbbf24",
    "alert_low":     "#3b82f6",
}

LIGHT_STYLESHEET = """
* { font-family: "Inter", "Segoe UI", "SF Pro Display", Arial, sans-serif; outline: none; }

QMainWindow, QDialog { background: #f6f8fc; color: #0f172a; }
QWidget { background: transparent; color: #0f172a; }

#topbar {
    background: #ffffff;
    border-bottom: 1px solid #e7ecf3;
    min-height: 60px;
    max-height: 60px;
}
#topbar_logo {
    font-size: 17px; font-weight: 800; color: #0f172a;
    letter-spacing: 1px; background: transparent;
}
#topbar_user { font-size: 13px; background: transparent; color: #64748b; }

#sidebar {
    background: #0b1220;
    min-width: 234px; max-width: 234px;
}
QPushButton#nav_btn {
    background: transparent; border: none;
    border-left: 3px solid transparent;
    color: #94a3b8;
    text-align: left; padding: 14px 24px;
    font-size: 13px; font-weight: 500;
}
QPushButton#nav_btn:hover {
    background: rgba(255,255,255,0.06); color: #ffffff;
    border-left-color: rgba(255,255,255,0.18);
}
QPushButton#nav_btn[active=true] {
    background: rgba(29,78,216,0.18); color: #ffffff;
    border-left: 3px solid #3b82f6; font-weight: 600;
}

#main_content { background: #f6f8fc; }
QStackedWidget { background: #f6f8fc; }

#video_panel { background: #0b1220; border-radius: 14px; border: 1px solid #e7ecf3; }
#video_toolbar {
    background: #ffffff; border-bottom: 1px solid #e7ecf3;
    border-radius: 14px 14px 0 0; min-height: 40px; max-height: 40px;
}
#camera_selector {
    background: #ffffff; color: #0f172a; border: 1px solid #e7ecf3;
    border-radius: 8px; padding: 5px 10px; font-size: 12px;
}
#camera_selector:hover { border-color: #1d4ed8; }

QFrame, #alert_panel, #dashboard_panel, #module_panel {
    background: #ffffff; border: 1px solid #e7ecf3; border-radius: 14px;
}

#alert_header {
    background: #ffffff; border: none; border-bottom: 1px solid #e7ecf3;
    border-radius: 14px 14px 0 0;
    padding: 11px 16px; font-size: 11px; letter-spacing: 1.5px;
    color: #1d4ed8; font-weight: 700;
}

QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff; color: #0f172a;
    border: 1.5px solid #e7ecf3; border-radius: 10px;
    padding: 9px 12px; font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #1d4ed8; }
QComboBox QAbstractItemView {
    background: #ffffff; color: #0f172a; border: 1px solid #e7ecf3;
    selection-background-color: #eef3ff; selection-color: #1d4ed8; outline: none;
}

QPushButton {
    background: #ffffff; color: #0f172a;
    border: 1px solid #e7ecf3; border-radius: 10px;
    padding: 8px 16px; font-size: 13px; font-weight: 500;
}
QPushButton:hover { background: #f1f5f9; border-color: #cbd5e1; }
QPushButton:disabled { background: #f1f5f9; color: #94a3b8; border-color: #e7ecf3; }
QPushButton#btn_primary {
    background: #1d4ed8; color: #fff; border: none;
    font-weight: 700; letter-spacing: 0.3px;
}
QPushButton#btn_primary:hover { background: #1e40af; }
QPushButton#btn_danger {
    background: #fef2f2; color: #e11d2e; border: 1px solid #fecdd3;
}
QPushButton#btn_danger:hover { background: #fee2e2; border-color: #e11d2e; }
QPushButton#btn_danger_sm {
    background: transparent; color: #e11d2e;
    border: 1px solid #fecdd3; border-radius: 8px;
}
QPushButton#btn_danger_sm:hover { background: #fef2f2; border-color: #e11d2e; }
QPushButton#btn_icon {
    background: #ffffff; border: 1px solid #e7ecf3;
    border-radius: 10px; font-size: 15px; color: #475569;
}
QPushButton#btn_icon:hover { background: #eef3ff; border-color: #1d4ed8; color: #1d4ed8; }

QTableWidget, QTreeWidget, QListWidget {
    background: #ffffff; color: #0f172a;
    border: none; border-radius: 0 0 14px 14px;
}
QListWidget#alert_list::item { padding: 8px 14px; border-bottom: 1px solid #f1f5f9; }
QListWidget::item:hover { background: #f8fafc; }
QListWidget::item:selected { background: #eef3ff; color: #1d4ed8; }
QHeaderView::section {
    background: #f8fafc; color: #64748b;
    border: none; border-bottom: 1px solid #e7ecf3;
    padding: 8px 12px; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
}

QTabWidget::pane {
    background: #ffffff; border: 1px solid #e7ecf3;
    border-top: none; border-radius: 0 0 12px 12px;
}
QTabBar::tab {
    background: #f1f5f9; color: #64748b;
    padding: 9px 22px; border: 1px solid #e7ecf3; border-bottom: none;
    font-size: 12px; font-weight: 500;
}
QTabBar::tab:selected { background: #ffffff; color: #1d4ed8; border-bottom: 2px solid #1d4ed8; }
QTabBar::tab:hover:!selected { background: #e2e8f0; }

QGroupBox {
    border: 1px solid #e7ecf3; border-radius: 12px;
    margin-top: 14px; padding-top: 12px;
    color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 14px; padding: 0 6px;
    color: #1d4ed8; background: #ffffff;
}

#section_title {
    color: #94a3b8; font-size: 11px; font-weight: 700;
    letter-spacing: 2px; background: transparent;
}
#status_dot_label, #status_text_label { background: transparent; font-size: 10px; color: #cbd5e1; }
#metric_value { color: #1d4ed8; font-size: 22px; font-weight: 700; background: transparent; }
#metric_label { color: #94a3b8; font-size: 9px; letter-spacing: 1.5px; background: transparent; }
#about_text { background: transparent; color: #334155; }
#sub_info_box { background: #eef3ff; border: 1px solid #bfdbfe; border-radius: 12px; }

QStatusBar {
    background: #ffffff; border-top: 1px solid #e7ecf3;
    color: #64748b; font-size: 11px;
}
QStatusBar::item { border: none; }

#status_panel { background: #0b1220; border-top: 1px solid rgba(255,255,255,0.06); }

QSlider::groove:horizontal { background: #e2e8f0; height: 4px; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #1d4ed8; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px; border: 2px solid #ffffff;
}
QSlider::sub-page:horizontal { background: #1d4ed8; border-radius: 2px; }

QProgressBar { background: #e2e8f0; border: none; border-radius: 3px; height: 6px; }
QProgressBar::chunk { background: #1d4ed8; border-radius: 3px; }

QScrollBar:vertical { background: transparent; width: 8px; border: none; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar:horizontal { background: transparent; height: 8px; border: none; }
QScrollBar::handle:horizontal { background: #cbd5e1; border-radius: 4px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

QCheckBox { color: #475569; spacing: 8px; }
QCheckBox::indicator {
    width: 32px; height: 17px; border-radius: 8px;
    background: #e2e8f0; border: 1px solid #cbd5e1;
}
QCheckBox::indicator:checked { background: #1d4ed8; border-color: #1d4ed8; }

QSplitter::handle { background: #e7ecf3; }

QToolTip {
    background: #0f172a; color: #f1f5f9;
    border: none; padding: 6px 10px; border-radius: 6px; font-size: 12px;
}

QMessageBox { background: #ffffff; }
QMessageBox QLabel { color: #0f172a; background: transparent; }
QMessageBox QPushButton { min-width: 80px; }
QInputDialog QLabel { color: #0f172a; background: transparent; }
"""

def get_stylesheet(theme: str = "dark") -> str:
    """Return the stylesheet for the given theme ('dark' or 'light')."""
    if theme == "light":
        return LIGHT_STYLESHEET
    return MAIN_STYLESHEET
