"""
Camera Stream Handler - Threaded video capture with queue buffering
Supports webcam, RTSP streams, IP cameras, video files
"""

import os
import cv2
import time
import threading
import queue
import numpy as np
from typing import Optional, Callable, Tuple
from utils.logger import get_logger

logger = get_logger("camera_stream")

class CameraStream:
    """
    Threaded camera/video stream with frame buffering.
    Prevents UI freezing by capturing frames on a dedicated thread.
    """

    def __init__(self, source, fps_target: int = 30, buffer_size: int = 5,
                 name: str = "CAM-01"):
        self.source = source
        self.fps_target = fps_target
        self.buffer_size = buffer_size
        self.name = name

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False
        self._error: Optional[str] = None

        self._frame_count = 0
        self._fps_actual = 0.0
        self._last_fps_time = time.time()
        self._last_fps_count = 0

        self._lock = threading.Lock()
        self._reconnect_attempts = 0
        self._max_reconnect = 5

        self._is_file = False
        self._file_fps = 0.0
        self._loop_file = True

    def start(self) -> bool:
        """Start the capture thread."""
        if self._running:
            return True
        success = self._open_capture()
        if not success:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(f"[{self.name}] Stream started: {self.source}")
        return True

    def stop(self):
        """Stop capture thread and release resources."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        self._release()
        logger.info(f"[{self.name}] Stream stopped.")

    def _open_capture(self) -> bool:
        """Open the video capture source."""
        try:
            if isinstance(self.source, str) and self.source.isdigit():
                src = int(self.source)
            else:
                src = self.source

            self._cap = cv2.VideoCapture(src)

            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

            self._is_file = (
                isinstance(src, str)
                and not src.lower().startswith(("rtsp://", "http://", "https://"))
                and os.path.isfile(src)
            )

            if self._is_file:

                file_fps = self._cap.get(cv2.CAP_PROP_FPS) or 0.0

                if file_fps <= 0 or file_fps > 240:
                    file_fps = float(self.fps_target)
                self._file_fps = file_fps
                logger.info(f"[{self.name}] Video file detected, FPS={file_fps:.1f}")
            else:

                if isinstance(src, int):
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if not self._cap.isOpened():
                self._error = f"Cannot open source: {self.source}"
                logger.error(f"[{self.name}] {self._error}")
                return False

            self._connected = True
            self._error = None
            self._reconnect_attempts = 0
            return True
        except Exception as e:
            self._error = str(e)
            logger.error(f"[{self.name}] Open error: {e}")
            return False

    def _release(self):
        if self._cap:
            self._cap.release()
            self._cap = None
        self._connected = False

        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break

    def _capture_loop(self):
        """Main capture loop running on background thread."""
        next_frame_time = time.perf_counter()

        while self._running:
            if not self._connected or self._cap is None:
                if not self._reconnect():
                    time.sleep(2)
                    continue
                next_frame_time = time.perf_counter()

            ret, frame = self._cap.read()
            if not ret or frame is None:

                if self._is_file:
                    if self._loop_file:
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        next_frame_time = time.perf_counter()
                        continue
                    else:
                        logger.info(f"[{self.name}] End of video file.")
                        self._running = False
                        break
                logger.warning(f"[{self.name}] Frame read failed, reconnecting...")
                self._connected = False
                continue

            self._frame_count += 1
            now = time.time()
            elapsed = now - self._last_fps_time
            if elapsed >= 1.0:
                self._fps_actual = (self._frame_count - self._last_fps_count) / elapsed
                self._last_fps_count = self._frame_count
                self._last_fps_time = now

            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass

            try:
                self._frame_queue.put_nowait(frame)
            except queue.Full:
                pass

            if self._is_file and self._file_fps > 0:
                frame_interval = 1.0 / self._file_fps
                next_frame_time += frame_interval
                sleep_for = next_frame_time - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:

                    next_frame_time = time.perf_counter()

    def _reconnect(self) -> bool:
        """Attempt to reconnect to stream."""
        if self._reconnect_attempts >= self._max_reconnect:
            self._error = "Max reconnection attempts reached"
            self._running = False
            return False
        self._reconnect_attempts += 1
        logger.info(f"[{self.name}] Reconnect attempt {self._reconnect_attempts}/{self._max_reconnect}")
        time.sleep(min(2 ** self._reconnect_attempts, 30))
        return self._open_capture()

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read the latest frame from the buffer."""
        try:
            frame = self._frame_queue.get(timeout=0.1)
            return True, frame
        except queue.Empty:
            return False, None

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get most recent frame, discarding older ones."""
        frame = None
        while not self._frame_queue.empty():
            try:
                frame = self._frame_queue.get_nowait()
            except queue.Empty:
                break
        return frame

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps(self) -> float:
        return round(self._fps_actual, 1)

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def resolution(self) -> Tuple[int, int]:
        if self._cap:
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return w, h
        return 0, 0

    def get_info(self) -> dict:
        """Return stream info dict."""
        return {
            "name": self.name,
            "source": str(self.source),
            "connected": self._connected,
            "fps": self.fps,
            "resolution": self.resolution,
            "frame_count": self._frame_count,
            "error": self._error
        }

class StreamManager:
    """
    Manages multiple camera streams.
    """

    def __init__(self):
        self._streams: dict[str, CameraStream] = {}
        self._lock = threading.Lock()

    def add_stream(self, name: str, source, **kwargs) -> CameraStream:
        """Add and start a new stream."""
        with self._lock:
            if name in self._streams:
                self._streams[name].stop()
            stream = CameraStream(source, name=name, **kwargs)
            stream.start()
            self._streams[name] = stream
            return stream

    def remove_stream(self, name: str):
        with self._lock:
            stream = self._streams.pop(name, None)
            if stream:
                stream.stop()

    def get_stream(self, name: str) -> Optional[CameraStream]:
        return self._streams.get(name)

    def get_all_streams(self) -> dict:
        return dict(self._streams)

    def stop_all(self):
        with self._lock:
            for stream in self._streams.values():
                stream.stop()
            self._streams.clear()
