# File: webcam_threading.py
from __future__ import annotations

import os
import time
import logging
from typing import Optional, Dict, Any, Literal

import numpy as np

try:
    import av  # PyAV for capture
except Exception:  # pragma: no cover
    av = None  # type: ignore

try:
    import pyvirtualcam
except Exception:  # pragma: no cover
    pyvirtualcam = None  # type: ignore

from PyQt5.QtCore import QThread, pyqtSignal  # GUI thread-friendly

logger = logging.getLogger(__name__)

StopReason = Literal["STOP_CALLED", "BACKEND_CLOSED", "NO_FRAMES", "EXCEPTION", "UNKNOWN"]


def _default_av_format() -> str:
    if os.name == "nt":
        return "dshow"
    # macOS / Linux best-effort fallbacks
    if sys_platform := os.environ.get("WSL_DISTRO_NAME"):
        return "v4l2"
    from sys import platform
    if platform == "darwin":
        return "avfoundation"
    return "v4l2"


def _build_default_input_options(fps: int = 30, width: int = 1280, height: int = 720) -> Dict[str, str]:
    """
    Conservative defaults that work for most DirectShow/AVFoundation/V4L2 inputs.
    Caller may override via ctor.
    """
    opts = {
        "rtbufsize": "100M",
        "framerate": str(int(max(1, fps))),
    }
    # Many stacks accept 'video_size', others accept 'video_size' via WxH
    opts["video_size"] = f"{int(width)}x{int(height)}"
    return opts


class WebcamThread(QThread):
    """
    PyAV-based capture thread with safe, explicit attributes.
    -> Fix: `input_options` is now defined in __init__ (not lazily in a property).
    """

    error_signal = pyqtSignal(str, object)   # (message, exception)
    info_signal  = pyqtSignal(str)           # status text for UI
    frame_signal = pyqtSignal(object)        # numpy BGR frame for UI/preview

    def __init__(
        self,
        input_device: str,
        style_instance: Any,
        style_params: Dict[str, Any] | None = None,
        *,
        input_options: Dict[str, str] | None = None,
        av_format: Optional[str] = None,
        out_backend: Optional[str] = "obs",
        enable_output: bool = True,
    ) -> None:
        super().__init__()
        self.input_device = input_device
        self.style = style_instance
        self.params: Dict[str, Any] = dict(style_params or {})

        # ✅ Define input_options in __init__
        fps = int(self.params.get("max_fps", 30) or 30)
        self.input_options: Dict[str, str] = dict(input_options or _build_default_input_options(fps=fps))

        # AV format
        self.av_format: str = av_format or _default_av_format()

        # Output (virtual cam) backend preference
        self.out_backend = out_backend
        self.enable_output = enable_output

        # Runtime state
        self._stop = False
        self._stopped_reason: StopReason = "UNKNOWN"
        self._container: Optional["av.container.InputContainer"] = None  # type: ignore
        self._stream = None
        self._vcam: Optional["pyvirtualcam.Camera"] = None  # type: ignore
        self.last_frame: Optional[np.ndarray] = None

        # Derived perf knobs
        self.frame_skip = int(self.params.get("frame_skip", 0) or 0)
        self.target_dt = 1.0 / float(max(1, fps))

    # ---- lifecycle helpers ----
    @property
    def stopped_reason(self) -> StopReason:
        return self._stopped_reason

    def stop(self) -> None:
        self._stop = True

    def update_params(self, new_params: Dict[str, Any]) -> None:
        """Hot-update perf/style params (thread-safe enough for UI sliders)."""
        self.params.update(new_params or {})
        fps = int(self.params.get("max_fps", 30) or 30)
        self.frame_skip = int(self.params.get("frame_skip", 0) or 0)
        self.target_dt = 1.0 / float(max(1, fps))
        # Keep input_options framerate in sync for restarts
        self.input_options["framerate"] = str(fps)

    # ---- open/close primitives ----
    def _open_input(self) -> bool:
        if av is None:
            self._emit_error("PyAV not installed; cannot open input.")
            self._stopped_reason = "BACKEND_CLOSED"
            return False
        try:
            logger.info("Attempting to open device via PyAV: device=%s format=%s options=%s",
                        self.input_device, self.av_format, self.input_options)
            self._container = av.open(self.input_device, format=self.av_format, options=self.input_options)
            self._stream = next((s for s in self._container.streams if s.type == "video"), None)
            if self._stream is None:
                self._emit_error("No video stream found in input device.")
                self._stopped_reason = "BACKEND_CLOSED"
                return False
            self._stream.thread_type = "AUTO"
            return True
        except Exception as e:
            logger.exception("Failed to open input device: %s", e)
            self._emit_error("Failed to open input device.", e)
            self._stopped_reason = "BACKEND_CLOSED"
            return False

    def _close_input(self) -> None:
        try:
            if self._container:
                self._container.close()
        except Exception:
            pass
        self._container = None
        self._stream = None

    def _open_output(self, width: int, height: int, fps: int) -> bool:
        if pyvirtualcam is None:
            self.info_signal.emit("Virtual camera unavailable (pyvirtualcam not installed).")
            return False
        try:
            # Prefer OBS backend if available; fallback to default
            kwargs = {"backend": self.out_backend} if self.out_backend else {}
            self._vcam = pyvirtualcam.Camera(width, height, fps, **kwargs)
            logger.info("Virtual camera ready: %sx%s @ %sfps (backend=%s)",
                        width, height, fps, self.out_backend)
            self.info_signal.emit(f"Virtual camera ready: {width}x{height} @ {fps}fps")
            return True
        except Exception as e:
            logger.exception("Failed to open virtual camera: %s", e)
            self._vcam = None
            self._emit_error("Failed to open virtual camera.", e)
            return False

    def _close_output(self) -> None:
        try:
            if self._vcam:
                self._vcam.close()
        except Exception:
            pass
        self._vcam = None

    # ---- run loop ----
    def run(self) -> None:  # noqa: C901
        self.info_signal.emit("WebcamThread started.")
        if not self._open_input():
            # Already emitted error
            self._cleanup(reason=self._stopped_reason or "BACKEND_CLOSED")
            return

        # Peek first frame to set output geometry
        width, height, fps = 1280, 720, int(self.params.get("max_fps", 30) or 30)
        first_frame = None
        empty_count = 0

        try:
            for packet in self._container.demux(self._stream):  # type: ignore[arg-type]
                if self._stop:
                    break
                for frame in packet.decode():
                    img = frame.to_ndarray(format="bgr24")
                    h, w, _ = img.shape
                    width, height = w, h
                    first_frame = img
                    break
                if first_frame is not None:
                    break
        except Exception as e:
            logger.exception("Error during initial demux/decode: %s", e)
            self._emit_error("Failed to read from input device.", e)

        if first_frame is None:
            self._stopped_reason = "NO_FRAMES"
            self._cleanup(reason="NO_FRAMES")
            return

        # Open output if requested (not needed when OBS Window-Captures the preview)
        if self.enable_output:
            self._open_output(width, height, fps)

        # Main decode loop
        last_emit = time.time()
        frame_i = 0

        try:
            # Push first frame immediately
            self.last_frame = self._process_frame(first_frame)
            self._push_output(self.last_frame)
            self.frame_signal.emit(self.last_frame)  # ✅ preview update

            for packet in self._container.demux(self._stream):  # type: ignore[arg-type]
                if self._stop:
                    break

                for frm in packet.decode():
                    img = frm.to_ndarray(format="bgr24")
                    empty_count = 0  # got a frame

                    # Frame skipping
                    do_skip = self.frame_skip > 0 and (frame_i % (self.frame_skip + 1)) != 0
                    frame_i += 1
                    if do_skip:
                        continue

                    # Style pipeline
                    self.last_frame = self._process_frame(img)
                    self._push_output(self.last_frame)
                    self.frame_signal.emit(self.last_frame)  # ✅ preview update

                    # Rate control (best-effort)
                    now = time.time()
                    elapsed = now - last_emit
                    if elapsed < self.target_dt:
                        time.sleep(self.target_dt - elapsed)
                    last_emit = time.time()

                # Periodic heartbeat
                if self.last_frame is not None and (time.time() - last_emit) > 1.5:
                    self.info_signal.emit("Streaming...")

        except Exception as e:
            logger.exception("WebcamThread exception: %s", e)
            self._emit_error("Capture loop crashed.", e)
            self._stopped_reason = "EXCEPTION"
        finally:
            reason = self._stopped_reason if self._stop is False else "STOP_CALLED"
            self._cleanup(reason=reason)

    # ---- helpers ----
    def _process_frame(self, bgr: np.ndarray) -> np.ndarray:
        """Apply current style safely. Expects/returns BGR frames."""
        try:
            # Many styles expect BGR or RGB—keep BGR contract internal.
            if hasattr(self.style, "apply"):
                # Try keyword arguments first (newer style format)
                try:
                    return self.style.apply(bgr, **self.params)
                except TypeError:
                    # Fallback to params dict (older style format)
                    return self.style.apply(bgr, params=self.params)
            else:
                return bgr
        except Exception as e:  # Never crash the capture on style errors
            logger.exception("Style apply failed: %s", e)
            self._emit_error("Style apply failed (fallback to passthrough).", e)
            return bgr

    def _push_output(self, bgr: np.ndarray) -> None:
        if self._vcam is None:
            return
        try:
            # pyvirtualcam expects RGB
            rgb = bgr[:, :, ::-1].copy()
            self._vcam.send(rgb)
            self._vcam.sleep_until_next_frame()
        except Exception as e:
            logger.exception("Virtual camera send failed: %s", e)
            self._emit_error("Virtual camera send failed.", e)

    def _emit_error(self, message: str, exc: Optional[BaseException] = None) -> None:
        try:
            self.error_signal.emit(message, exc)
        except Exception:
            # Signals not connected or UI already torn down
            logger.error("Error (no-signal): %s", message, exc_info=exc)

    def _cleanup(self, *, reason: StopReason) -> None:
        self._stopped_reason = reason
        self._close_input()
        self._close_output()
        self.info_signal.emit(f"WebcamThread stopped. reason={reason}")