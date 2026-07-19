"""
Model Setup Dialog - First-run model download wizard
"""

import os
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LOGO_PATH = os.path.join(_ASSETS_DIR, "logo.png")

class ModelDownloadWorker(QThread):
    """Background thread for model downloads."""

    progress = Signal(str, int, int, bool)
    log_message = Signal(str)
    finished = Signal(bool)

    def run(self):
        try:
            from utils.model_downloader import download_all_models

            def cb(name, current, total, success):
                self.progress.emit(name, current, total, success)
                status = "✓" if success else "✗"
                self.log_message.emit(f"  [{status}] {name}")

            self.log_message.emit("Starting model downloads...")
            results = download_all_models(progress_cb=cb)
            success = all(results.values())
            self.log_message.emit("\nDownload complete!" if success else "\nSome downloads failed.")
            self.finished.emit(success)
        except Exception as e:
            self.log_message.emit(f"\nError: {e}")
            self.finished.emit(False)

class ModelSetupDialog(QDialog):
    """
    First-run dialog that checks for and downloads required models.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AlertEye — Model Setup")
        self.setFixedSize(520, 440)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0b1322, stop:1 #0a0f1c);
                color: #d6e1f0;
            }
            QLabel { background: transparent; }
            QPushButton {
                background: #15203a; color: #aebfdc; border: 1px solid #233149;
                border-radius: 6px; padding: 7px 16px; font-size: 11px;
            }
            QPushButton:hover { background: #1b2a49; color: #fff; }
            QPushButton#btn_primary {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: #fff; border: none; font-weight: 700;
            }
            QPushButton#btn_primary:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4f92ff, stop:1 #2f6ef0);
            }
            QPushButton:disabled { background: #0e1628; color: #3a4d6e; }
        """)
        self._setup_ui()
        self._check_existing_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(16)

        title = QLabel()
        title.setAlignment(Qt.AlignCenter)
        _pix = QPixmap(LOGO_PATH)
        if not _pix.isNull():
            title.setPixmap(_pix.scaledToWidth(128, Qt.SmoothTransformation))
        else:
            title.setText("ALERTEYE")
            title.setStyleSheet(
                "color: #5b9bff; font-size: 24px; font-weight: 700; letter-spacing: 4px;"
            )

        subtitle = QLabel("AI Powered · Always Watching")
        subtitle.setStyleSheet("color: #6b7e9c; font-size: 11px; font-weight: 600; letter-spacing: 2px;")
        subtitle.setAlignment(Qt.AlignCenter)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1d2941;")

        info = QLabel(
            "AI detection models are required for surveillance features.\n"
            "Click Download to fetch pretrained YOLOv8 models automatically."
        )
        info.setStyleSheet("color: #5a6a80; font-size: 11px;")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)

        self.model_status = QTextEdit()
        self.model_status.setReadOnly(True)
        self.model_status.setFixedHeight(140)
        self.model_status.setStyleSheet(
            "background: #070c18; border: 1px solid #1d2941; border-radius: 8px; "
            "color: #8ba0c4; font-family: 'Courier New'; font-size: 10px; padding: 8px;"
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 6)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #1a2742; border: none; border-radius: 4px; } "
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #2563eb, stop:1 #3b82f6); border-radius: 4px; }"
        )

        btn_row = QHBoxLayout()
        self.btn_skip = QPushButton("Skip (Use CPU Fallback)")
        self.btn_skip.clicked.connect(self.accept)
        self.btn_download = QPushButton("Download Models")
        self.btn_download.setObjectName("btn_primary")
        self.btn_download.setFixedWidth(160)
        self.btn_download.clicked.connect(self._start_download)
        self.btn_ok = QPushButton("Launch AlertEye →")
        self.btn_ok.setObjectName("btn_primary")
        self.btn_ok.setFixedWidth(180)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setVisible(False)
        btn_row.addWidget(self.btn_skip)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_download)
        btn_row.addWidget(self.btn_ok)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(sep)
        layout.addWidget(info)
        layout.addWidget(self.model_status)
        layout.addWidget(self.progress_bar)
        layout.addLayout(btn_row)

    def _check_existing_models(self):
        """Check which models are already downloaded."""
        from utils.model_downloader import MODEL_REGISTRY, model_exists
        lines = []
        all_present = True
        for name, info in MODEL_REGISTRY.items():
            exists = model_exists(info["filename"])
            status = "✓" if exists else "○"
            color = "#3b82f6" if exists else "#3a4555"
            lines.append(f'{status}  {info["description"]}')
            if not exists:
                all_present = False

        self.model_status.setPlainText("\n".join(lines))

        if all_present:
            self.btn_download.setText("Models Ready ✓")
            self.btn_download.setEnabled(False)
            self.btn_ok.setVisible(True)
            self.btn_skip.setVisible(False)

    def _start_download(self):
        self.btn_download.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.model_status.clear()
        self.model_status.append("Initializing downloads...\n")

        self._worker = ModelDownloadWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.log_message.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, name, current, total, success):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_log(self, message):
        self.model_status.append(message)
        self.model_status.verticalScrollBar().setValue(
            self.model_status.verticalScrollBar().maximum()
        )

    def _on_finished(self, success):
        if success:
            self.model_status.append("\n✓ All models ready!")
            self.btn_ok.setVisible(True)
        else:
            self.model_status.append(
                "\n⚠ Some models failed. The system will use fallback detection."
            )
            self.btn_ok.setVisible(True)
            self.btn_ok.setText("Continue Anyway →")
        self.btn_skip.setVisible(False)
