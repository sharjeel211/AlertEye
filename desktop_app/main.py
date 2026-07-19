"""
AlertEye — Intelligent Surveillance System v2.0
Main entry point.
FIX: --standalone flag skips login for local testing without web portal.
     Also auto-detects if server is unreachable and offers standalone mode.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtGui import QFont, QIcon

from ui.main_window import MainWindow
from utils.logger import setup_logger
from utils.config_manager import ConfigManager

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AlertEye")
    app.setApplicationVersion("2.0.0")

    icon_path = os.path.join(PROJECT_ROOT, "assets", "logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    font = QFont("Segoe UI", 9)
    app.setFont(font)

    config = ConfigManager()
    logger = setup_logger()
    logger.info("AlertEye starting up...")

    standalone = "--standalone" in sys.argv

    auth = None
    if not standalone:
        server_url = config.get("server_url", default="https://alerteye.online")
        try:
            import requests
            requests.get(server_url, timeout=3)

            from ui.login_window import LoginWindow
            from utils.auth_manager import AuthManager
            auth = AuthManager(server_url=server_url)
            login_win = LoginWindow(auth)
            result = login_win.exec()
            if result != QDialog.Accepted:
                sys.exit(0)
        except Exception:

            reply = QMessageBox.question(
                None,
                "Server Not Found",
                "Cannot connect to AlertEye web portal.\n\n"
                "Run in Standalone Mode?\n"
                "(All detection modules will be enabled without login)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                sys.exit(0)
            auth = None

    window = MainWindow(config, auth=auth)
    window.show()
    window.raise_()

    logger.info("AlertEye ready.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
