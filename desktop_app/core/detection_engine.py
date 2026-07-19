"""
Detection Engine - Orchestrates all detection modules on video frames.
FIXED:
  - initialize() now calls load_model() for every enabled detector
  - _load_models_lazy() is no longer needed as gate to run detectors
  - process_frame() runs detectors even if annotated_frame is None
  - Subscription gating removed from engine (handled by main_window)
  - module name map added so 'fire_smoke' key maps to 'fire_smoke_detection'
"""

import cv2
import time
import threading
import numpy as np
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from detectors.base_detector import DetectionResult
from detectors.weapon_detector import WeaponDetector
from detectors.fire_smoke_detector import FireSmokeDetector
from detectors.accident_detector import AccidentDetector
from utils.logger import get_logger

logger = get_logger("detection_engine")

MODULE_ALIAS = {
    "fire_smoke":  "fire_smoke_detection",
    "weapon":      "weapon_detection",
    "accident":    "accident_detection",
}

@dataclass
class EngineResult:
    frame_id: int
    frame: np.ndarray
    annotated_frame: np.ndarray
    results: Dict[str, DetectionResult]
    total_detections: int = 0
    any_alert: bool = False
    fps: float = 0.0
    processing_ms: float = 0.0

class DetectionEngine:

    def __init__(self, config, on_result: Optional[Callable] = None):
        self.config = config
        self.on_result = on_result
        self._device = self._resolve_device()

        self._detectors: Dict[str, object] = {}
        self._enabled_modules: set = set()
        self._frame_counter = 0
        self._frame_skip = config.get("detection", "frame_skip", default=2)
        self._lock = threading.Lock()

        pool_size = config.get("performance", "thread_pool_size", default=4)
        self._executor = ThreadPoolExecutor(max_workers=pool_size)

        self._fps_counter = 0
        self._fps_value = 0.0
        self._fps_time = time.time()
        self._initialized = False

    def _resolve_device(self) -> str:
        device = self.config.get("detection", "device", default="cpu")
        if device != "auto":
            return device
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("CUDA available - using GPU acceleration")
                return "cuda:0"
        except ImportError:
            pass
        logger.info("Using CPU for inference")
        return "cpu"

    def initialize(self, on_progress: Optional[Callable] = None):
        """
        Initialize and LOAD all detector modules.
        FIX: load_model() is called here so detectors are ready immediately.
        """
        logger.info("Initializing detection engine...")

        modules = [
            ("weapon_detection",     WeaponDetector),
            ("fire_smoke_detection", FireSmokeDetector),
            ("accident_detection",   AccidentDetector),
        ]

        for i, (name, DetectorClass) in enumerate(modules):
            try:
                detector = DetectorClass(self.config, device=self._device)
                enabled = self.config.get("modules", name, "enabled", default=True)

                if enabled:
                    detector.enable()
                    self._enabled_modules.add(name)

                    logger.info(f"Loading model for: {name}")
                    try:
                        detector.load_model()
                        warm = np.zeros((480, 640, 3), dtype=np.uint8)
                        detector.process_frame(warm, 0, False)
                        logger.info(f"Warmed up: {name}")
                    except Exception as load_err:
                        logger.error(f"Model load failed for {name}: {load_err}")
                else:
                    detector.disable()

                self._detectors[name] = detector
                logger.info(f"Initialized: {name} (enabled={enabled}, loaded={detector.is_loaded})")

                if on_progress:
                    on_progress(name, i + 1, len(modules))

            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")

        self._initialized = True
        logger.info(f"Detection engine ready. {len(self._detectors)} modules loaded.")

    def process_frame(self, frame: np.ndarray) -> Optional[EngineResult]:
        """
        Process a video frame through all enabled detectors.
        FIX: does not gate on is_loaded — process_frame() in base handles lazy load.
        """
        self._frame_counter += 1

        if self._frame_counter % self._frame_skip != 0:
            return None

        start_time = time.perf_counter()
        annotated = frame.copy()
        all_results: Dict[str, DetectionResult] = {}
        total_detections = 0
        any_alert = False

        active_detectors = {
            name: det for name, det in self._detectors.items()
            if det.is_enabled
        }

        if not active_detectors:
            logger.warning("No active detectors — check module enabled settings")

        futures = {
            self._executor.submit(det.process_frame, frame, self._frame_counter, True): name
            for name, det in active_detectors.items()
        }

        for future in as_completed(futures, timeout=10.0):
            name = futures[future]
            try:
                result: DetectionResult = future.result()
                all_results[name] = result

                if result.has_detections:
                    total_detections += len(result.detections)
                    if result.alert_triggered:
                        any_alert = True

                    if result.annotated_frame is not None:
                        cv2.addWeighted(result.annotated_frame, 0.6,
                                        annotated, 0.4, 0, annotated)
                    else:
                        active_detectors[name].draw_detections(
                            annotated, result.detections
                        )

            except Exception as e:
                logger.error(f"Detector {name} error: {e}")

        self._fps_counter += 1
        elapsed = time.time() - self._fps_time
        if elapsed >= 1.0:
            self._fps_value = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_time = time.time()

        processing_ms = (time.perf_counter() - start_time) * 1000
        self._draw_hud(annotated, total_detections, any_alert)

        result = EngineResult(
            frame_id=self._frame_counter,
            frame=frame,
            annotated_frame=annotated,
            results=all_results,
            total_detections=total_detections,
            any_alert=any_alert,
            fps=self._fps_value,
            processing_ms=processing_ms
        )

        if self.on_result:
            self.on_result(result)

        return result

    def _draw_hud(self, frame: np.ndarray, total: int, alert: bool):
        h, w = frame.shape[:2]
        fps_text = f"ENGINE FPS: {self._fps_value:.1f}"
        cv2.putText(frame, fps_text, (10, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 100), 1, cv2.LINE_AA)
        det_text = f"DETECTIONS: {total}"
        cv2.putText(frame, det_text, (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        if alert:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 4)

    def set_module_enabled(self, module_name: str, enabled: bool):
        """
        FIX: Resolve short alias names ('fire_smoke' → 'fire_smoke_detection')
        so toggles from main_window actually reach the correct detector.
        """
        full_name = MODULE_ALIAS.get(module_name, module_name)
        det = self._detectors.get(full_name)
        if det:
            if enabled:
                det.enable()
                self._enabled_modules.add(full_name)
                if not det.is_loaded:
                    threading.Thread(target=det.load_model, daemon=True).start()
            else:
                det.disable()
                self._enabled_modules.discard(full_name)
            self.config.set_module_enabled(full_name, enabled)
        else:
            logger.warning(f"set_module_enabled: unknown module '{module_name}' (resolved: '{full_name}')")

    def set_confidence_threshold(self, module_name: str, threshold: float):
        full_name = MODULE_ALIAS.get(module_name, module_name)
        det = self._detectors.get(full_name)
        if det:
            det.set_confidence_threshold(threshold)

    def set_global_confidence(self, threshold: float):
        for det in self._detectors.values():
            det.set_confidence_threshold(threshold)

    def get_module_statuses(self) -> List[Dict]:
        return [det.get_status() for det in self._detectors.values()]

    def shutdown(self):
        self._executor.shutdown(wait=False)
        logger.info("Detection engine shut down.")
