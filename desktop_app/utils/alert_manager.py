"""
Alert Manager - Handles alarm sounds, screenshots, and video clip saving
"""

import os
import time
import threading
import cv2
import numpy as np
from datetime import datetime
from typing import Optional
from utils.logger import get_logger, DetectionLogger

logger = get_logger("alert_manager")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AlertManager:
    """
    Manages detection alerts: sounds, screenshots, recordings, cooldowns.
    Thread-safe via internal locks.
    """

    def __init__(self, config):
        self.config = config
        self.detection_logger = DetectionLogger(config.abs_path("logs"))

        self._screenshot_dir = config.abs_path("screenshots")
        self._recordings_dir = config.abs_path("recordings")
        os.makedirs(self._screenshot_dir, exist_ok=True)
        os.makedirs(self._recordings_dir, exist_ok=True)

        self._alert_cooldowns = {}
        self._lock = threading.Lock()
        self._sound_enabled = config.get("alerts", "sound_enabled", default=True)
        self._cooldown = config.get("alerts", "alert_cooldown_seconds", default=10)

        self._video_writers = {}
        self._sound_thread: Optional[threading.Thread] = None

        self._audio_backend = None
        self._init_audio()

    def _init_audio(self):
        """Detect best available audio backend (no third-party install required on Windows)."""
        import platform
        if platform.system() == "Windows":

            self._audio_backend = "winsound"
            return

        try:
            import simpleaudio
            self._audio_backend = "simpleaudio"
            return
        except ImportError:
            pass
        logger.warning("No audio backend available — sound alerts disabled.")

    def trigger_alert(self, alert_type: str, confidence: float,
                      frame: Optional[np.ndarray] = None,
                      camera_id: str = "CAM-01",
                      metadata: dict = None):
        """
        Main entry: called whenever a detection occurs.
        Handles cooldowns, sound, screenshot, recording log.
        """
        if not self._check_cooldown(alert_type):
            return False

        logger.warning(f"ALERT: {alert_type} detected | conf={confidence:.2f} | cam={camera_id}")

        self.detection_logger.log_detection(alert_type, confidence, camera_id, metadata)

        if frame is not None and self.config.get("alerts", "screenshot_on_alert", default=True):
            self._save_screenshot(frame, alert_type, camera_id)

        if self._sound_enabled:
            self._play_alert_sound(alert_type)

        return True

    def _check_cooldown(self, alert_type: str) -> bool:
        """Returns True if enough time has passed since last alert of this type."""
        with self._lock:
            last = self._alert_cooldowns.get(alert_type, 0)
            now = time.time()
            if now - last < self._cooldown:
                return False
            self._alert_cooldowns[alert_type] = now
            return True

    def _save_screenshot(self, frame: np.ndarray, alert_type: str, camera_id: str):
        """Save a screenshot of the detection frame."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        safe_type = alert_type.replace(" ", "_").lower()
        safe_cam = camera_id.replace(" ", "_").replace("/", "-")
        filename = f"{timestamp}_{safe_cam}_{safe_type}.jpg"
        filepath = os.path.join(self._screenshot_dir, filename)
        try:
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            logger.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"Screenshot save failed: {e}")

    def start_recording(self, camera_id: str, frame_size: tuple, fps: float = 20.0):
        """Start recording a video clip for an alert."""
        duration = self.config.get("alerts", "record_duration_seconds", default=15)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_cam = camera_id.replace(" ", "_").replace("/", "-")
        filename = f"{timestamp}_{safe_cam}_alert.mp4"
        filepath = os.path.join(self._recordings_dir, filename)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(filepath, fourcc, fps, frame_size)
        end_time = time.time() + duration

        with self._lock:

            if camera_id in self._video_writers:
                old_writer, _ = self._video_writers[camera_id]
                old_writer.release()
            self._video_writers[camera_id] = (writer, end_time)

        logger.info(f"Recording started: {filename} ({duration}s)")

    def write_recording_frame(self, camera_id: str, frame: np.ndarray):
        """Write a frame to active recording if one exists."""
        with self._lock:
            info = self._video_writers.get(camera_id)
            if info is None:
                return
            writer, end_time = info
            if time.time() > end_time:
                writer.release()
                del self._video_writers[camera_id]
                return
            writer.write(frame)

    def stop_recording(self, camera_id: str):
        """Manually stop recording for a camera."""
        with self._lock:
            info = self._video_writers.pop(camera_id, None)
            if info:
                info[0].release()

    def ring_alarm(self):
        """Immediately start/extend the looping alarm, bypassing the cooldown.
        Called the instant the video shows a red alert so the siren is in sync."""
        self._play_alert_sound("threat")

    def stop_alarm(self, mute_seconds: float = 8.0):
        """Manually silence the alarm now and suppress re-triggering for a short
        window, so the Stop button works even while the threat is still in view."""
        self._muted_until = time.time() + mute_seconds
        self._alarm_until = 0
        if self._audio_backend == "winsound":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        self._alarm_active = False

    def _play_alert_sound(self, alert_type: str):
        """Ring a continuous looping alarm. Any module's detection (re)triggers
        it; it keeps ringing for `alarm_duration` seconds after the last hit."""
        if time.time() < getattr(self, "_muted_until", 0):
            return
        self._alarm_until = time.time() + self.config.get(
            "alerts", "alarm_duration", default=8
        )
        if getattr(self, "_alarm_active", False):
            return
        self._alarm_active = True
        self._sound_thread = threading.Thread(target=self._alarm_loop, daemon=True)
        self._sound_thread.start()

    def _alarm_loop(self):
        try:
            sound_path = self.config.abs_path(
                self.config.get("alerts", "sound_file", default="assets/sounds/alert.wav")
            )
            if self._audio_backend == "winsound":
                import winsound
                if os.path.exists(sound_path):
                    winsound.PlaySound(
                        sound_path,
                        winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
                    )
                    while time.time() < self._alarm_until:
                        time.sleep(0.2)
                    winsound.PlaySound(None, winsound.SND_PURGE)
                else:
                    while time.time() < self._alarm_until:
                        winsound.Beep(880, 500)
                        time.sleep(0.12)
            elif self._audio_backend == "simpleaudio" and os.path.exists(sound_path):
                import simpleaudio as sa
                wave_obj = sa.WaveObject.from_wave_file(sound_path)
                while time.time() < self._alarm_until:
                    wave_obj.play().wait_done()
            else:
                while time.time() < self._alarm_until:
                    print("\a", end="", flush=True)
                    time.sleep(0.6)
        except Exception as e:
            logger.debug(f"Alarm loop error: {e}")
        finally:
            self._alarm_active = False

    def _play_system_beep(self, alert_type: str):
        """Fallback: system beep at varying frequencies."""
        freq_map = {
            "weapon": 880, "fire": 660, "smoke": 660,
            "accident": 770, "default": 440
        }
        key = next((k for k in freq_map if k in alert_type.lower()), "default")
        freq = freq_map[key]
        try:
            if self._audio_backend == "winsound":
                import winsound
                winsound.Beep(freq, 600)
            else:

                print("\a", end="", flush=True)
        except Exception as e:
            logger.debug(f"System beep failed: {e}")

    def set_sound_enabled(self, enabled: bool):
        self._sound_enabled = enabled

    def cleanup(self):
        """Release all resources."""
        with self._lock:
            for writer, _ in self._video_writers.values():
                writer.release()
            self._video_writers.clear()
