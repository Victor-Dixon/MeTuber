# File: src/video/webcam_threading.py
from __future__ import annotations
import cv2
import logging
import threading
import time
from typing import Optional, Literal

logger = logging.getLogger(__name__)

StopReason = Literal["STOP_CALLED", "NO_FRAMES", "EXCEPTION", "BACKEND_CLOSED", "UNKNOWN"]

class WebcamThread(threading.Thread):
    def __init__(self, device: str = "video=OBS Virtual Camera", fps: int = 15, backend: int = cv2.CAP_DSHOW):
        super().__init__(daemon=True)
        self.device = device
        self.backend = backend
        self.fps = max(1, fps)
        self._stop_event = threading.Event()
        self._stopped_reason: StopReason = "UNKNOWN"
        self._cap: Optional[cv2.VideoCapture] = None
        self._auto_restart = True
        self._restart_backoff = 0.5  # seconds, grows to 4s

    @property
    def stopped_reason(self) -> StopReason:
        return self._stopped_reason

    def stop(self) -> None:
        self._auto_restart = False
        self._stop_event.set()

    def _open(self) -> bool:
        self._cap = cv2.VideoCapture(self.device, self.backend)
        ok = bool(self._cap and self._cap.isOpened())
        if ok:
            logger.info("Virtual camera initialized: 1920x1080 @ %sfps", self.fps)
        return ok

    def _close(self) -> None:
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
        self._cap = None

    def run(self) -> None:
        logger.info("webcam_threading - WebcamThread started.")
        while not self._stop_event.is_set():
            try:
                if not self._open():
                    logger.error("Failed to open device: %s", self.device)
                    self._stopped_reason = "BACKEND_CLOSED"
                    if not self._auto_restart:
                        break
                    time.sleep(self._restart_backoff)
                    self._restart_backoff = min(4.0, self._restart_backoff * 2.0)
                    continue

                # Capture loop
                target_dt = 1.0 / float(self.fps)
                consecutive_empty = 0
                while not self._stop_event.is_set():
                    ok, frame = self._cap.read()
                    if not ok or frame is None:
                        consecutive_empty += 1
                        if consecutive_empty >= 10:  # ~0.6s at 15 fps
                            self._stopped_reason = "NO_FRAMES"
                            logger.warning("No frames received from %s; stopping.", self.device)
                            break
                        time.sleep(0.05)
                        continue

                    consecutive_empty = 0
                    # TODO: route frame to sinks
                    # Keep running even without consumers; do not auto-stop.
                    time.sleep(target_dt)

                # Decide loop exit behavior
                self._close()
                if self._stop_event.is_set():
                    self._stopped_reason = "STOP_CALLED"
                    break

                # If we broke due to NO_FRAMES, attempt auto-restart
                if self._auto_restart:
                    logger.info("Auto-restarting webcam thread after reason=%s", self._stopped_reason)
                    time.sleep(self._restart_backoff)
                    self._restart_backoff = min(4.0, self._restart_backoff * 2.0)
                    continue
                else:
                    break

            except Exception as e:
                logger.exception("WebcamThread exception: %s", e)
                self._stopped_reason = "EXCEPTION"
                self._close()
                if not self._auto_restart:
                    break
                time.sleep(self._restart_backoff)
                self._restart_backoff = min(4.0, self._restart_backoff * 2.0)

        logger.info("webcam_threading - WebcamThread stopped. reason=%s", self._stopped_reason)
