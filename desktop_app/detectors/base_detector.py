"""
Base Detector - Abstract base class for all detection modules
FIX: confirmation_frames lowered to 1, ALERT_THREAT_LEVELS expanded,
     alert_triggered now fires on ANY detection not just HIGH/CRITICAL.
"""

import os
import time
import numpy as np
import cv2
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from utils.logger import get_logger

logger = get_logger("base_detector")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass
class Detection:
    """Single detection result."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    track_id: Optional[int] = None
    extra: dict = field(default_factory=dict)
    threat_level: str = "LOW"
    color: Tuple[int, int, int] = (0, 255, 0)

@dataclass
class DetectionResult:
    """Aggregated result from one detector on one frame."""
    module_name: str
    detections: List[Detection]
    frame_id: int = 0
    processing_time_ms: float = 0.0
    alert_triggered: bool = False
    annotated_frame: Optional[np.ndarray] = None

    @property
    def has_detections(self) -> bool:
        return len(self.detections) > 0

    @property
    def max_confidence(self) -> float:
        if not self.detections:
            return 0.0
        return max(d.confidence for d in self.detections)

THREAT_COLORS = {
    "LOW":      (0, 200, 100),
    "MEDIUM":   (0, 165, 255),
    "HIGH":     (0, 50, 255),
    "CRITICAL": (0, 0, 255),
    "INFO":     (200, 200, 0),
}

class BaseDetector(ABC):
    """
    Abstract base class for all AlertEye detection modules.
    FIXED: alert fires on ANY detection, confirmation_frames=1 by default.
    """

    MODULE_NAME = "base_detector"
    MODULE_DISPLAY_NAME = "Base Detector"
    DEFAULT_CONFIDENCE = 0.25

    ALERT_THREAT_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def __init__(self, config, device: str = "auto"):
        self.config = config
        self._enabled = True
        self._model = None
        self._model_loaded = False
        self._device = self._resolve_device(device)
        self._conf_threshold = config.get(
            "modules", self.MODULE_NAME, "confidence_threshold",
            default=self.DEFAULT_CONFIDENCE
        )
        self._frame_counter = 0
        self._logger = get_logger(self.MODULE_NAME)

        self._confirmation_frames = config.get(
            "detection", "confirmation_frames", default=1
        )
        self._consecutive_detections = 0
        self._confirmed_alert = False

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @abstractmethod
    def load_model(self) -> bool:
        ...

    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        ...

    def process_frame(self, frame: np.ndarray, frame_id: int = 0,
                      draw_overlay: bool = True) -> DetectionResult:
        """
        Public entry point. Handles enable check, timing, overlay drawing.
        FIXED: alert_triggered fires as soon as ANY detection appears.
        """
        if not self._enabled:
            return DetectionResult(
                module_name=self.MODULE_NAME, detections=[], frame_id=frame_id
            )

        if not self._model_loaded:
            self.load_model()

        start = time.perf_counter()
        try:
            result = self.detect(frame)
        except Exception as e:
            self._logger.error(f"Detection error in {self.MODULE_NAME}: {e}")
            result = DetectionResult(
                module_name=self.MODULE_NAME, detections=[], frame_id=frame_id
            )

        result.frame_id = frame_id
        result.processing_time_ms = (time.perf_counter() - start) * 1000

        if result.has_detections:
            self._consecutive_detections += 1
        else:
            self._consecutive_detections = 0

        if self._consecutive_detections >= self._confirmation_frames:
            result.alert_triggered = True
            self._consecutive_detections = 0
        else:
            result.alert_triggered = False

        if draw_overlay and result.has_detections:
            annotated = frame.copy()
            self.draw_detections(annotated, result.detections)
            result.annotated_frame = annotated

        return result

    def draw_detections(self, frame: np.ndarray, detections: List[Detection]):
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = THREAT_COLORS.get(det.threat_level, det.color)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{det.label} {det.confidence:.0%}"
            if det.track_id is not None:
                label = f"#{det.track_id} {label}"
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        self._draw_module_badge(frame)

    def _draw_module_badge(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        text = f"◉ {self.MODULE_DISPLAY_NAME}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        overlay = frame.copy()
        cv2.rectangle(overlay, (w - tw - 12, 6), (w - 4, th + 14), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, text, (w - tw - 8, th + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 160), 1, cv2.LINE_AA)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_loaded(self) -> bool:
        return self._model_loaded

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def set_confidence_threshold(self, threshold: float):
        self._conf_threshold = max(0.0, min(1.0, threshold))

    def get_status(self) -> dict:
        return {
            "module": self.MODULE_NAME,
            "display_name": self.MODULE_DISPLAY_NAME,
            "enabled": self._enabled,
            "loaded": self._model_loaded,
            "device": self._device,
            "confidence_threshold": self._conf_threshold
        }
