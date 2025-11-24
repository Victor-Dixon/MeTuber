# File: webcam_threading.py
from __future__ import annotations

import os
import sys
import time
import logging
import platform as platform_module
import subprocess
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


def _list_dshow_devices():
    """Return list of DirectShow device names via ffmpeg (Windows only)."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True, timeout=5
        )
        out = (proc.stderr or "") + (proc.stdout or "")
        names = []
        for line in out.splitlines():
            line = line.strip()
            # Lines look like: [dshow @ ...] "Logitech HD Webcam C270"
            if '"' in line and "DirectShow" not in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    device_name = parts[1]
                    # Skip virtual outputs (like OBS Virtual Camera) as input sources
                    if "Virtual Camera" not in device_name and device_name:
                        names.append(device_name)
        # Remove duplicates while preserving order
        return list(dict.fromkeys(names))
    except Exception as e:
        logger.warning(f"Could not enumerate DirectShow devices: {e}")
        return []


def _probe_opencv_device():
    """Try to discover a working device index via OpenCV as a fallback (returns tuple: (index, backend))."""
    try:
        import cv2
        
        # Log available backends
        backends = []
        if hasattr(cv2, 'videoio_registry'):
            backends = cv2.videoio_registry.getBackends()
            logger.info(f"Available OpenCV backends: {backends}")
        
        # On Windows, DirectShow doesn't support index-based access well
        # Use MSMF (Media Foundation) which supports index access, or fall back to default
        if os.name == "nt":
            # Try MSMF first (better for index-based access on Windows)
            backend = cv2.CAP_MSMF if hasattr(cv2, 'CAP_MSMF') else cv2.CAP_ANY
            logger.info(f"Scanning OpenCV devices with MSMF backend (supports index-based access)")
        else:
            backend = cv2.CAP_ANY
            logger.info(f"Scanning OpenCV devices with default backend")
        
        for idx in range(10):  # probe up to 10 indices
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    # Try to read a frame to verify it's actually working
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        logger.info(f"Found working OpenCV device at index {idx} with backend {backend}")
                        cap.release()
                        return (idx, backend)
                    cap.release()
                else:
                    cap.release()
            except Exception as e:
                logger.debug(f"OpenCV device {idx} probe failed: {e}")
                continue
        
        # If no devices found with MSMF on Windows, try default backend
        if os.name == "nt" and backend != cv2.CAP_ANY:
            logger.info("No devices found with MSMF, trying default backend...")
            for idx in range(10):
                try:
                    cap = cv2.VideoCapture(idx)  # Default backend
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            logger.info(f"Found working OpenCV device at index {idx} with default backend")
                            cap.release()
                            return (idx, cv2.CAP_ANY)
                        cap.release()
                    else:
                        cap.release()
                except Exception as e:
                    logger.debug(f"OpenCV device {idx} probe with default backend failed: {e}")
                    continue
                    
    except ImportError:
        logger.warning("OpenCV not available for device probing")
    except Exception as e:
        logger.warning(f"OpenCV device probe failed: {e}")
    return None


def _default_av_format() -> str:
    if os.name == "nt":
        return "dshow"
    # macOS / Linux best-effort fallbacks
    if sys_platform := os.environ.get("WSL_DISTRO_NAME"):
        return "v4l2"
    if platform_module.system() == "Darwin":
        return "avfoundation"
    return "v4l2"


def _build_default_input_options(fps: int = 30, width: int = 1280, height: int = 720) -> Dict[str, str]:
    """
    Low-latency defaults optimized for real-time video capture.
    Small buffer size and no-buffer flags minimize delay.
    """
    opts = {
        "rtbufsize": "512K",  # Small buffer for low latency (was 256M - way too large!)
        "framerate": str(int(max(1, fps))),
        "fflags": "nobuffer",  # Disable buffering
        "flags": "low_delay",  # Low delay mode
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
        self._use_opencv = False
        self._opencv_cap = None

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
    def _resolve_device_for_windows(self):
        """Windows-specific: resolve device name to exact DirectShow name."""
        if not isinstance(self.input_device, str):
            return self.input_device
            
        # If already properly formatted with exact name, keep it
        device_str = self.input_device
        if device_str.lower().startswith("video="):
            device_name = device_str[6:]  # Remove "video=" prefix
        else:
            device_name = device_str
            
        # Try to find exact match or similar match from DirectShow
        dshow_devices = _list_dshow_devices()
        
        if not dshow_devices:
            logger.warning("No DirectShow devices found. Check camera connection and Windows Camera privacy settings.")
            return self.input_device
            
        # Look for exact match first
        for dev in dshow_devices:
            if dev.lower() == device_name.lower():
                resolved = f"video={dev}"
                logger.info(f"Resolved device '{self.input_device}' to exact match: '{resolved}'")
                return resolved
                
        # Look for partial match (e.g., "C270" matches "Logitech HD Webcam C270")
        for dev in dshow_devices:
            if device_name.lower() in dev.lower() or dev.lower() in device_name.lower():
                resolved = f"video={dev}"
                logger.info(f"Resolved device '{self.input_device}' to similar match: '{resolved}'")
                return resolved
                
        # No match found, try first available device
        if dshow_devices:
            resolved = f"video={dshow_devices[0]}"
            logger.warning(f"Could not find device '{self.input_device}', using first available: '{resolved}'")
            return resolved
            
        return self.input_device

    def _open_input(self) -> bool:
        # Force DirectShow on Windows
        if os.name == "nt":
            self.av_format = "dshow"
            logger.info("Windows detected: forcing DirectShow backend")
        
        # Windows-specific: resolve device name to exact DirectShow device
        if os.name == "nt" and self.av_format == "dshow":
            self.input_device = self._resolve_device_for_windows()
            
        # Try PyAV first (preferred method)
        if av is not None:
            last_error = None
            for attempt in range(3):
                try:
                    logger.info("Attempt %d: Opening device via PyAV: device=%s format=%s options=%s",
                                attempt + 1, self.input_device, self.av_format, self.input_options)
                    self._container = av.open(self.input_device, format=self.av_format, options=self.input_options)
                    self._stream = next((s for s in self._container.streams if s.type == "video"), None)
                    if self._stream is None:
                        logger.warning("No video stream found in PyAV container")
                        if self._container:
                            self._container.close()
                        self._container = None
                        break  # Try fallback
                    self._stream.thread_type = "AUTO"
                    logger.info("Successfully opened camera via PyAV: %s", self.input_device)
                    return True
                except Exception as e:
                    last_error = e
                    logger.warning(f"PyAV attempt {attempt + 1} failed: {e}")
                    if self._container:
                        try:
                            self._container.close()
                        except:
                            pass
                        self._container = None
                    if attempt < 2:  # Don't sleep on last attempt
                        time.sleep(0.5 * (attempt + 1))  # Progressive backoff
            
            if last_error:
                logger.warning("PyAV failed, trying OpenCV DirectShow fallback...")
        else:
            logger.warning("PyAV not available, trying OpenCV DirectShow fallback...")
        
        # Fallback: Try OpenCV with MSMF backend (Windows) or default (Linux/Mac)
        try:
            import cv2
            logger.info("Attempting OpenCV fallback...")
            
            # Log available backends
            if hasattr(cv2, 'videoio_registry'):
                backends = cv2.videoio_registry.getBackends()
                logger.info(f"Available OpenCV backends: {backends}")
            
            # Try to find working device index (returns tuple: (index, backend) or None)
            probe_result = _probe_opencv_device()
            if probe_result is not None:
                working_idx, backend = probe_result
                logger.info(f"Using OpenCV device index {working_idx} with backend {backend}")
                # Create a wrapper that uses OpenCV for capture
                self._opencv_cap = cv2.VideoCapture(working_idx, backend)
                if self._opencv_cap.isOpened():
                    # Set buffer size to 1 frame for minimal latency
                    try:
                        self._opencv_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        logger.info("OpenCV buffer size set to 1 frame for low latency")
                    except Exception as e:
                        logger.debug(f"Could not set OpenCV buffer size: {e}")
                    
                    # Verify it works
                    ret, frame = self._opencv_cap.read()
                    if ret and frame is not None:
                        logger.info(f"Successfully opened camera via OpenCV at index {working_idx} (backend: {backend})")
                        self._use_opencv = True
                        return True
                    else:
                        self._opencv_cap.release()
                        self._opencv_cap = None
                else:
                    self._opencv_cap = None
            else:
                logger.warning("OpenCV device probe found no working devices")
        except ImportError:
            logger.warning("OpenCV not available for fallback")
        except Exception as e:
            logger.exception("OpenCV fallback failed: %s", e)
        
        # All methods failed
        error_msg = "Failed to open input device with all methods (PyAV and OpenCV)."
        if os.name == "nt":
            error_msg += "\n\nWindows Troubleshooting:\n"
            error_msg += "1. Check Settings → Privacy & Security → Camera:\n"
            error_msg += "   - Enable 'Camera access'\n"
            error_msg += "   - Enable 'Let apps access your camera'\n"
            error_msg += "   - Enable 'Allow desktop apps to access your camera' (IMPORTANT!)\n"
            error_msg += "2. Close all apps using the camera:\n"
            error_msg += "   - Teams, Zoom, Discord, OBS, Chrome, etc.\n"
            error_msg += "   - Check Task Manager → Processes → sort by GPU/Power\n"
            error_msg += "3. Try unplugging and replugging the camera\n"
            error_msg += "4. Try a different USB port (prefer rear motherboard ports)\n"
            dshow_devices = _list_dshow_devices()
            if dshow_devices:
                error_msg += f"\n5. Available DirectShow devices: {', '.join(dshow_devices)}"
            else:
                error_msg += "\n5. No DirectShow devices detected (check camera connection and drivers)"
        
        last_error = last_error if 'last_error' in locals() else None
        self._emit_error(error_msg, last_error)
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
        
        # Close OpenCV capture if used
        try:
            if self._opencv_cap:
                self._opencv_cap.release()
        except Exception:
            pass
        self._opencv_cap = None
        self._use_opencv = False

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

        # Determine capture method
        if self._use_opencv and self._opencv_cap:
            self._run_opencv_loop()
        else:
            self._run_pyav_loop()

    def _run_pyav_loop(self) -> None:
        """Run the capture loop using PyAV."""
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

                    # Rate control (best-effort) - only sleep if we're ahead of schedule
                    now = time.time()
                    elapsed = now - last_emit
                    if elapsed < self.target_dt:
                        time.sleep(self.target_dt - elapsed)
                    # If we're behind (elapsed > target_dt), don't sleep - process next frame immediately
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

    def _run_opencv_loop(self) -> None:
        """Run the capture loop using OpenCV (MSMF on Windows, default on Linux/Mac)."""
        import cv2
        
        # Get first frame to set output geometry
        width, height, fps = 1280, 720, int(self.params.get("max_fps", 30) or 30)
        first_frame = None
        empty_count = 0

        try:
            ret, first_frame = self._opencv_cap.read()
            if ret and first_frame is not None:
                h, w = first_frame.shape[:2]
                width, height = w, h
                logger.info(f"OpenCV capture initialized: {width}x{height}")
            else:
                logger.error("Failed to read first frame from OpenCV")
                self._stopped_reason = "NO_FRAMES"
                self._cleanup(reason="NO_FRAMES")
                return
        except Exception as e:
            logger.exception("Error during OpenCV initial read: %s", e)
            self._emit_error("Failed to read from OpenCV device.", e)
            self._stopped_reason = "NO_FRAMES"
            self._cleanup(reason="NO_FRAMES")
            return

        # Open output if requested
        if self.enable_output:
            self._open_output(width, height, fps)

        # Main capture loop
        last_emit = time.time()
        frame_i = 0

        try:
            # Push first frame immediately
            self.last_frame = self._process_frame(first_frame)
            self._push_output(self.last_frame)
            self.frame_signal.emit(self.last_frame)  # ✅ preview update

            while not self._stop:
                # For low latency: flush buffer by reading and discarding old frames
                # This ensures we always get the latest frame
                latest_frame = None
                for _ in range(3):  # Read up to 3 frames to flush buffer
                    ret, img = self._opencv_cap.read()
                    if ret and img is not None:
                        latest_frame = img
                    else:
                        break
                
                if latest_frame is None:
                    empty_count += 1
                    if empty_count > 30:  # 30 consecutive empty frames
                        logger.warning("Too many empty frames from OpenCV, stopping")
                        self._stopped_reason = "NO_FRAMES"
                        break
                    time.sleep(0.01)  # Small delay before retry
                    continue

                empty_count = 0  # got a frame
                img = latest_frame  # Use the latest frame

                # Frame skipping
                do_skip = self.frame_skip > 0 and (frame_i % (self.frame_skip + 1)) != 0
                frame_i += 1
                if do_skip:
                    continue

                # Style pipeline
                self.last_frame = self._process_frame(img)
                self._push_output(self.last_frame)
                self.frame_signal.emit(self.last_frame)  # ✅ preview update

                # Rate control (best-effort) - only sleep if we're ahead of schedule
                now = time.time()
                elapsed = now - last_emit
                if elapsed < self.target_dt:
                    time.sleep(self.target_dt - elapsed)
                # If we're behind (elapsed > target_dt), don't sleep - process next frame immediately
                last_emit = time.time()

                # Periodic heartbeat
                if self.last_frame is not None and (time.time() - last_emit) > 1.5:
                    self.info_signal.emit("Streaming...")

        except Exception as e:
            logger.exception("OpenCV capture loop exception: %s", e)
            self._emit_error("OpenCV capture loop crashed.", e)
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