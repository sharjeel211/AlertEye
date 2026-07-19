"""
Accident Detection Module
The specialized model directly outputs accident labels, so the label IS the
detection. Current model classes (nc=3): accident, moderate, severe.
Plain object classes (bike, car, person) are never alerts on their own.
"""

import cv2
import numpy as np
from typing import List, Optional
from detectors.base_detector import BaseDetector, Detection, DetectionResult, THREAT_COLORS
from utils.model_downloader import get_best_model_path
from utils.logger import get_logger

logger = get_logger("accident_detector")

ACCIDENT_THREAT_LEVELS = {
    "anomaly":              "CRITICAL",
    "severe":               "CRITICAL",
    "accident":             "CRITICAL",
    "moderate":             "HIGH",
    "car_car_accident":     "CRITICAL",
    "car_bike_accident":    "CRITICAL",
    "bike_person_accident": "CRITICAL",
    "car_object_accident":  "HIGH",
    "bike_bike_accident":   "HIGH",
}

NON_ALERT_CLASSES = {"normal", "bike", "car", "person"}

class AccidentDetector(BaseDetector):

    MODULE_NAME = "accident_detection"
    MODULE_DISPLAY_NAME = "Accident/Collision"
    DEFAULT_CONFIDENCE = 0.80

    def __init__(self, config, device: str = "auto"):
        super().__init__(config, device)

    def load_model(self) -> bool:
        try:
            from ultralytics import YOLO
            model_path = get_best_model_path("accident_detection")
            logger.info(f"Loading accident model: {model_path}")
            self._model = YOLO(model_path)
            self._model_loaded = True
            logger.info(f"Accident detector loaded (device={self._device})")
            return True
        except Exception as e:
            logger.error(f"Failed to load accident model: {e}")
            self._model_loaded = False
            return False

    def detect(self, frame: np.ndarray) -> DetectionResult:
        detections = []

        try:
            results = self._model.predict(
                source=frame,
                conf=self._conf_threshold,
                iou=0.4,
                device=self._device,
                verbose=False,
                max_det=20,
            )

            for r in results:
                if r.boxes is None:
                    continue
                names = r.names
                for box in r.boxes:
                    cls_id = int(box.cls[0].item())
                    label  = str(names.get(cls_id, cls_id)).lower()
                    conf   = float(box.conf[0].item())

                    threat = self._classify_accident(label)
                    if threat is None:

                        continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    detections.append(Detection(
                        label=label.replace("_", " ").upper(),
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        threat_level=threat,
                        color=THREAT_COLORS.get(threat, (0, 0, 255)),
                        extra={"type": "accident", "class_name": label},
                    ))

        except Exception as e:
            logger.error(f"AccidentDetector.detect error: {e}")

        return DetectionResult(
            module_name=self.MODULE_NAME,
            detections=detections,
            alert_triggered=bool(detections)
        )

    def _classify_accident(self, label: str) -> Optional[str]:
        label = label.lower()
        if label in NON_ALERT_CLASSES:
            return None
        if label in ACCIDENT_THREAT_LEVELS:
            return ACCIDENT_THREAT_LEVELS[label]
        if "accident" in label or "anomaly" in label:
            return "CRITICAL"
        return None

    def draw_detections(self, frame: np.ndarray, detections: List[Detection]):
        h, w = frame.shape[:2]
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = det.color
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"{det.label} [{det.confidence:.0%}]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), color, -1)
            cv2.putText(frame, label, (x1 + 3, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        critical = [d for d in detections if d.threat_level == "CRITICAL"]
        if critical:
            banner = "ACCIDENT / COLLISION DETECTED"
            (bw, bh), _ = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (0, 0), (w, bh + 14), (0, 0, 180), -1)
            cv2.putText(frame, banner, ((w - bw) // 2, bh + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
