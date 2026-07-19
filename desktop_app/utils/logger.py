"""
Logger Utility - Centralized logging for AlertEye
"""

import os
import logging
import colorlog
from datetime import datetime
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

def setup_logger(name: str = "alerteye", level=logging.DEBUG) -> logging.Logger:
    """Configure and return the root application logger."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "red,bg_white"
        }
    ))

    log_file = os.path.join(LOG_DIR, "alerteye.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a child logger."""
    return logging.getLogger(f"alerteye.{name}")

class DetectionLogger:
    """Logs detection events to a structured detection history file."""

    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "detections.log")
        self._logger = get_logger("detections")

    def log_detection(self, detection_type: str, confidence: float,
                      camera_id: str = "CAM-01", metadata: dict = None):
        """Log a detection event."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        entry = {
            "timestamp": timestamp,
            "type": detection_type,
            "confidence": round(confidence, 3),
            "camera": camera_id,
            "metadata": metadata or {}
        }

        import json
        line = json.dumps(entry)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        self._logger.info(f"[{camera_id}] {detection_type} detected (conf={confidence:.2f})")

    def get_recent_detections(self, limit: int = 100) -> list:
        """Return the most recent detection entries."""
        if not os.path.exists(self.log_file):
            return []
        import json
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries[-limit:]
