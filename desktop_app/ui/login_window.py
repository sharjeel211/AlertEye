"""
AlertEye Desktop — Login Window
Modern login screen with subscription status feedback.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap

import os
from utils.auth_manager import AuthManager

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LOGO_PATH = os.path.join(_ASSETS_DIR, "logo.png")

class LoginWorker(QThread):
    """Background thread for login API call."""
    finished = Signal(dict)

    def __init__(self, auth: AuthManager, email: str, password: str):
        super().__init__()
        self.auth = auth
        self.email = email
        self.password = password

    def run(self):
        result = self.auth.login(self.email, self.password)
        self.finished.emit(result)

class LoginWindow(QDialog):
    login_success = Signal(object)

    def __init__(self, auth_manager: AuthManager, parent=None):
        super().__init__(parent)
        self.auth = auth_manager
        self.setWindowTitle("AlertEye — Sign In")
        self.setFixedSize(420, 560)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self._setup_ui()
        self._load_saved_email()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0b1322, stop:1 #0a0f1c);
            }
            QLabel { color: #d6e1f0; background: transparent; }
            QLineEdit {
                border: 1.5px solid #233149;
                border-radius: 9px;
                padding: 11px 14px;
                font-size: 13px;
                background: #111a2e;
                color: #e3ecf8;
            }
            QLineEdit:focus { border-color: #3b82f6; background: #131f38; }
            QPushButton#btnLogin {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: none;
                border-radius: 9px;
                padding: 12px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton#btnLogin:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4f92ff, stop:1 #2f6ef0);
            }
            QPushButton#btnLogin:disabled { background: #24324d; color: #6b7e9c; }
            QCheckBox { color: #9fb3d4; font-size: 12px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 38, 44, 40)
        layout.setSpacing(0)

        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(LOGO_PATH)
        if not pixmap.isNull():
            logo_lbl.setPixmap(pixmap.scaledToWidth(150, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("🛡️")
            logo_lbl.setStyleSheet("font-size: 48px;")
        layout.addWidget(logo_lbl)
        layout.addSpacing(6)

        subtitle = QLabel("AI Powered · Always Watching")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6b7e9c; font-size: 11px; font-weight: 600; "
                               "letter-spacing: 2px; margin-bottom: 28px;")
        layout.addWidget(subtitle)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size: 12px; min-height: 18px; margin-bottom: 8px;")
        layout.addWidget(self.lbl_status)

        lbl_email = QLabel("Email Address")
        lbl_email.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;")
        layout.addWidget(lbl_email)
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("you@company.com")
        layout.addWidget(self.txt_email)
        layout.addSpacing(12)

        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;")
        layout.addWidget(lbl_pass)
        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("••••••••")
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.returnPressed.connect(self._do_login)
        layout.addWidget(self.txt_password)
        layout.addSpacing(16)

        self.btn_login = QPushButton("Sign In")
        self.btn_login.setObjectName("btnLogin")
        self.btn_login.setFixedHeight(44)
        self.btn_login.clicked.connect(self._do_login)
        layout.addWidget(self.btn_login)
        layout.addSpacing(16)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1d2941; background: #1d2941; max-height: 1px;")
        layout.addWidget(sep)
        layout.addSpacing(12)

        lbl_server = QLabel("Server URL")
        lbl_server.setStyleSheet("font-size: 10px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px;")
        layout.addWidget(lbl_server)
        self.txt_server = QLineEdit()
        self.txt_server.setText(self.auth.server_url)
        self.txt_server.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(self.txt_server)

        layout.addStretch()

    def _load_saved_email(self):
        email = self.auth.get_saved_email()
        if email:
            self.txt_email.setText(email)
            self.txt_password.setFocus()

    def _set_status(self, msg, color='#64748b'):
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(f"font-size: 12px; min-height: 18px; margin-bottom: 8px; color: {color};")

    def _do_login(self):
        email = self.txt_email.text().strip()
        password = self.txt_password.text()
        server = self.txt_server.text().strip()

        if not email or not password:
            self._set_status("Please enter your email and password.", '#dc2626')
            return

        self.auth.server_url = server
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in...")
        self._set_status("Connecting to server...", '#2563eb')

        self._worker = LoginWorker(self.auth, email, password)
        self._worker.finished.connect(self._on_login_result)
        self._worker.start()

    def _on_login_result(self, result):
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign In")

        if result.get('success'):
            if not result.get('subscription_active'):
                self._set_status(
                    "⚠️ Subscription inactive or expired.\nModules are locked. Contact your administrator.",
                    '#f59e0b'
                )

            else:
                days = result.get('days_remaining', 0)
                self._set_status(f"✓ Welcome back! Subscription active ({days} days remaining)", '#10b981')
            self.login_success.emit(self.auth)
            self.accept()
        else:
            error = result.get('error', 'Login failed')
            self._set_status(f"✗ {error}", '#dc2626')
