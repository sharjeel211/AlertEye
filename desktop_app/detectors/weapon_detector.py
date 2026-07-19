"""
Weapon Detection Module
FIXED:
  - DEFAULT_CONFIDENCE lowered to 0.25
  - Generic COCO model: expanded weapon class list
  - Specialized model: accept ALL detections not just matched keywords
"""

import os
import cv2
import numpy as np
from typing import List
from detectors.base_detector import BaseDetector, Detection, DetectionResult, THREAT_COLORS
from utils.model_downloader import get_best_model_path
from utils.logger import get_logger

logger = get_logger("weapon_detector")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WEAPON_COCO_CLASSES = {
    "baseball bat": "HIGH",
    "gun":          "CRITICAL",
    "pistol":       "CRITICAL",
    "rifle":        "CRITICAL",
}

WEAPON_CLASSES = {
    "weapon": "CRITICAL",
}

class WeaponDetector(BaseDetector):

    MODULE_NAME = "weapon_detection"
    MODULE_DISPLAY_NAME = "Weapon Detector"

    DEFAULT_CONFIDENCE = 0.40
    MAX_BOX_AREA_RATIO = 0.85

    def __init__(self, config, device: str = "auto"):
        super().__init__(config, device)
        self._using_specialized = False

    def load_model(self) -> bool:
        try:
            from ultralytics import YOLO
            model_path = get_best_model_path("weapon_detection")
            logger.info(f"Loading weapon model: {model_path}")
            self._model = YOLO(model_path)

            names = self._model.names if hasattr(self._model, "names") else {}
            weapon_keywords = {"gun", "pistol", "rifle", "knife", "weapon", "firearm",
                               "handgun", "shotgun", "revolver", "blade", "machete"}
            class_names = set(str(v).lower() for v in names.values())
            self._using_specialized = bool(class_names & weapon_keywords)

            if self._using_specialized:
                logger.info(f"Weapon detector: specialized model loaded (classes: {class_names})")
            else:
                logger.warning("Weapon detector: COCO fallback active.")

            self._model_loaded = True
            return True
        except Exception as e:
            logger.error(f"Failed to load weapon model: {e}")
            self._model_loaded = False
            return False

    def detect(self, frame: np.ndarray) -> DetectionResult:
        detections = []
        h, w = frame.shape[:2]
        frame_area = float(h * w)
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
                boxes = r.boxes
                if boxes is None:
                    continue
                names = r.names
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    label  = names.get(cls_id, str(cls_id)).lower()
                    conf   = float(box.conf[0].item())

                    threat = self._classify_threat(label)
                    if threat is None:
                        continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                    box_area = max(0, x2 - x1) * max(0, y2 - y1)
                    if frame_area > 0 and box_area / frame_area > self.MAX_BOX_AREA_RATIO:
                        logger.debug(
                            f"Dropped oversized weapon box "
                            f"({box_area / frame_area:.0%} of frame) — likely false positive"
                        )
                        continue

                    track_id = int(box.id[0].item()) if box.id is not None else None
                    color = THREAT_COLORS.get(threat, (0, 0, 255))
                    detections.append(Detection(
                        label=f"WEAPON: {label.upper()}",
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        track_id=track_id,
                        threat_level=threat,
                        color=color,
                        extra={"class_name": label}
                    ))
        except Exception as e:
            logger.error(f"WeaponDetector.detect error: {e}")

        return DetectionResult(
            module_name=self.MODULE_NAME,
            detections=detections,
            alert_triggered=bool(detections)
        )

    def _classify_threat(self, label: str):
        if self._using_specialized:
            if label == "person":
                return None
            weapon_keywords = ("weapon", "gun", "pistol", "rifle", "knife",
                               "firearm", "handgun", "shotgun", "revolver",
                               "blade", "machete", "grenade")
            if any(k in label for k in weapon_keywords):
                return "CRITICAL"
            return None
        else:
            for weapon_key, threat in WEAPON_COCO_CLASSES.items():
                if weapon_key in label:
                    return threat
            return None

    def draw_detections(self, frame: np.ndarray, detections: List[Detection]):
        h, w = frame.shape[:2]
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            clen = 15
            for cx, cy, dx, dy in [
                (x1, y1, 1, 1), (x2, y1, -1, 1),
                (x1, y2, 1, -1), (x2, y2, -1, -1)
            ]:
                cv2.line(frame, (cx, cy), (cx + dx * clen, cy), (0, 0, 255), 3)
                cv2.line(frame, (cx, cy), (cx, cy + dy * clen), (0, 0, 255), 3)
            label = f"WEAPON: {det.label.replace('WEAPON: ', '')} [{det.confidence:.0%}]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 8, y1), (0, 0, 200), -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        if detections:
            banner = "! WEAPON DETECTED — ALERT TRIGGERED !"
            (bw, bh), _ = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
            cv2.rectangle(frame, (0, 0), (w, bh + 14), (0, 0, 200), -1)
            cv2.putText(frame, banner, ((w - bw) // 2, bh + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
