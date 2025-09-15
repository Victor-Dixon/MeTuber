# File: tests/test_webcamthread_smoke.py
from webcam_threading import WebcamThread

class DummyStyle:
    def apply(self, frame, **params): return frame

def test_smoke_ctor_has_required_attrs():
    wt = WebcamThread(input_device="video=C270 HD WEBCAM", style_instance=DummyStyle())
    for attr in ["input_device", "style", "params", "input_options", "av_format", "frame_skip", "target_dt"]:
        assert hasattr(wt, attr)
