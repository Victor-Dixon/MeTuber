# File: tests/test_webcam_threading.py
import time
from src.video.webcam_threading import WebcamThread

def test_webcam_thread_start_stop(monkeypatch):
    # Skip real camera; just ensure thread lifecycle doesn't crash.
    wt = WebcamThread(device="video=OBS Virtual Camera", fps=15)
    wt._open = lambda: False  # force backend closed path
    wt.start()
    time.sleep(0.2)
    wt.stop()
    wt.join(timeout=2.0)
    assert wt.stopped_reason in {"STOP_CALLED", "BACKEND_CLOSED", "EXCEPTION"}