"""
Configuration Manager - Handles all application settings
"""

import os
import sys
import json
import yaml
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = sys._MEIPASS
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_CONFIG = {
    "app": {
        "version": "1.0.0",
        "theme": "dark",
        "language": "en"
    },
    "camera": {
        "default_source": 0,
        "resolution_width": 1280,
        "resolution_height": 720,
        "fps_target": 30,
        "buffer_size": 5
    },
    "detection": {
        "confidence_threshold": 0.45,
        "nms_threshold": 0.4,
        "max_detections": 50,
        "frame_skip": 2,
        "gpu_enabled": True,
        "device": "auto"
    },
    "modules": {
        "weapon_detection": {
            "enabled": True,
            "confidence_threshold": 0.50,
            "model_path": "models/weapon_detection.pt",
            "alert_on_detect": True
        },
        "fire_smoke_detection": {
            "enabled": True,
            "confidence_threshold": 0.45,
            "model_path": "models/fire_smoke.pt",
            "alert_on_detect": True
        },
        "accident_detection": {
            "enabled": True,
            "confidence_threshold": 0.45,
            "model_path": "models/accident_detection.pt",
            "alert_on_detect": True
        }
    },
    "alerts": {
        "sound_enabled": True,
        "sound_file": "assets/sounds/alert.wav",
        "alert_cooldown_seconds": 10,
        "screenshot_on_alert": True,
        "record_on_alert": True,
        "record_duration_seconds": 15
    },
    "storage": {
        "logs_path": "logs",
        "screenshots_path": "screenshots",
        "recordings_path": "recordings",
        "max_log_size_mb": 100,
        "max_storage_gb": 10,
        "auto_cleanup": True
    },
    "display": {
        "show_fps": True,
        "show_confidence": True,
        "show_labels": True,
        "show_bounding_boxes": True,
        "bbox_thickness": 2,
        "overlay_opacity": 0.7
    },
    "performance": {
        "thread_pool_size": 4,
        "detection_queue_size": 10,
        "ui_update_interval_ms": 33
    }
}

class ConfigManager:
    """Manages application configuration with file persistence."""

    def __init__(self, config_file: str = None):
        self.config_file = config_file or os.path.join(
            PROJECT_ROOT, "config", "settings.json"
        )
        self.config = {}
        self._load()

    def _load(self):
        """Load config from file or create with defaults."""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    saved = json.load(f)
                self.config = self._deep_merge(DEFAULT_CONFIG.copy(), saved)
            except Exception:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Persist config to disk."""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, *keys, default=None):
        """Get config value by dot-path keys."""
        val = self.config
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key, default)
            else:
                return default
        return val

    def set(self, value, *keys):
        """Set config value by dot-path keys."""
        d = self.config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
        self.save()

    def get_module_config(self, module_name: str) -> dict:
        """Get configuration for a specific detection module."""
        return self.config.get("modules", {}).get(module_name, {})

    def set_module_enabled(self, module_name: str, enabled: bool):
        """Enable or disable a detection module."""
        self.set(enabled, "modules", module_name, "enabled")

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dicts, override takes priority."""
        result = base.copy()
        for key, val in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = self._deep_merge(result[key], val)
            else:
                result[key] = val
        return result

    @property
    def project_root(self) -> str:
        return PROJECT_ROOT

    def abs_path(self, relative_path: str) -> str:
        """Convert relative config path to absolute path."""
        return os.path.join(PROJECT_ROOT, relative_path)
