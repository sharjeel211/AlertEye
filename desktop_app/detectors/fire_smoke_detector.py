"""
Fire & Smoke Detection Module
FIXED:
  - _color_based_fire_detect is properly indented inside the class
  - HSV thresholds tightened to stop false positives on signboards/clothing
  - Generic COCO model YOLO path disabled — only HSV runs when no fire model
"""

import cv2
import numpy as np
from typing import List
from detectors.base_detector import BaseDetector, Detection, DetectionResult, THREAT_COLORS
from utils.model_downloader import get_best_model_path
from utils.logger import get_logger

logger = get_logger("fire_smoke_detector")

FIRE_SMOKE_CLASSES = {
    "fire":      "CRITICAL",
    "flame":     "CRITICAL",
    "smoke":     "HIGH",
    "wildfire":  "CRITICAL",
    "burning":   "CRITICAL",
    "explosion": "CRITICAL",
    "blaze":     "CRITICAL",
    "flare":     "HIGH",
    "ember":     "HIGH",
    "smog":      "HIGH",
}

def _is_fire_smoke_label(label: str):
    label_lower = label.lower()
    for key, threat in FIRE_SMOKE_CLASSES.items():
        if key in label_lower:
            return threat
    return None

class FireSmokeDetector(BaseDetector):

    MODULE_NAME = "fire_smoke_detection"
    MODULE_DISPLAY_NAME = "Fire & Smoke"
    DEFAULT_CONFIDENCE = 0.25

    def __init__(self, config, device: str = "auto"):
        super().__init__(config, device)
        self._is_specialized = False

    def load_model(self) -> bool:
        try:
            from ultralytics import YOLO
            model_path = get_best_model_path("fire_smoke")
            logger.info(f"Loading fire/smoke model: {model_path}")
            self._model = YOLO(model_path)

            all_names = set(str(v).lower() for v in self._model.names.values())
            nc = len(all_names)
            fire_keywords = {"fire", "flame", "smoke", "wildfire", "blaze", "burning"}
            self._is_specialized = bool(all_names & fire_keywords)

            if nc >= 70:
                logger.warning(
                    "fire_smoke.pt is a generic COCO model — YOLO path disabled. "
                    "Only HSV color detection will run. "
                    "Download the real fire model and save as models/fire_smoke.pt"
                )
                self._model = None
                self._is_specialized = False
            elif self._is_specialized:
                logger.info(f"Fire/smoke: specialized model loaded (classes: {all_names})")
            else:
                logger.warning("Fire/smoke: unknown model — treating as specialized.")
                self._is_specialized = True

            self._model_loaded = True
            return True
        except Exception as e:
            logger.error(f"Failed to load fire/smoke model: {e}")
            self._model_loaded = True
            self._model = None
            return True

    def detect(self, frame: np.ndarray) -> DetectionResult:
        detections = []

        if self._model is not None and self._is_specialized:
            try:
                results = self._model.predict(
                    source=frame,
                    conf=self._conf_threshold,
                    iou=0.4,
                    device=self._device,
                    verbose=False,
                    max_det=20
                )
                for r in results:
                    if r.boxes is None:
                        continue
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        label  = r.names.get(cls_id, str(cls_id))
                        conf   = float(box.conf[0].item())
                        threat = _is_fire_smoke_label(label) or "HIGH"
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        detections.append(Detection(
                            label=label.title(),
                            confidence=conf,
                            bbox=(x1, y1, x2, y2),
                            threat_level=threat,
                            color=(0, 50, 255),
                            extra={"source": "yolo", "specialized": True}
                        ))
            except Exception as e:
                logger.error(f"FireSmokeDetector YOLO error: {e}")
        else:
            detections.extend(self._color_based_fire_detect(frame))

        return DetectionResult(
            module_name=self.MODULE_NAME,
            detections=detections,
            alert_triggered=bool(detections)
        )

    def _color_based_fire_detect(self, frame: np.ndarray) -> List[Detection]:
        detections = []
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            mask_a = cv2.inRange(hsv, np.array([0,   180, 180], np.uint8),
                                       np.array([15,  255, 255], np.uint8))

            mask_c = cv2.inRange(hsv, np.array([165, 180, 180], np.uint8),
                                       np.array([180, 255, 255], np.uint8))

            mask = cv2.bitwise_or(mask_a, mask_c)

            _, v_channel = cv2.threshold(hsv[:, :, 2], 200, 255, cv2.THRESH_BINARY)
            mask = cv2.bitwise_and(mask, v_channel)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            h, w = frame.shape[:2]
            frame_area = h * w
            min_area = frame_area * 0.01

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area:
                    continue

                x, y, bw, bh = cv2.boundingRect(cnt)
                roi_hsv = hsv[y:y+bh, x:x+bw]
                mean_v = float(roi_hsv[:, :, 2].mean())
                mean_s = float(roi_hsv[:, :, 1].mean())

                if mean_v < 200 or mean_s < 150:
                    continue

                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                if hull_area > 0 and (area / hull_area) > 0.85:
                    continue

                aspect_ratio = bw / bh if bh > 0 else 0
                if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                    continue

                conf = min(0.90, 0.50 + (area / frame_area) * 10)
                detections.append(Detection(
                    label="Fire (color)",
                    confidence=round(conf, 2),
                    bbox=(x, y, x + bw, y + bh),
                    threat_level="HIGH",
                    color=(0, 69, 255),
                    extra={"source": "color_hsv", "area_px": int(area)}
                ))

        except Exception as e:
            logger.error(f"Color fire detection error: {e}")

        return detections

    def draw_detections(self, frame: np.ndarray, detections: List[Detection]):
        h, w = frame.shape[:2]
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 80, 255), 2)
            cv2.rectangle(frame, (x1 + 1, y1 + 1), (x2 - 1, y2 - 1), (0, 160, 255), 1)
            label = f"FIRE: {det.label} [{det.confidence:.0%}]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 8, y1), (0, 50, 200), -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1, cv2.LINE_AA)
        if detections:
            banner = "FIRE / SMOKE DETECTED"
            (bw, bh), _ = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (0, 0), (w, bh + 14), (0, 50, 200), -1)
            cv2.putText(frame, banner, ((w - bw) // 2, bh + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2, cv2.LINE_AA)
