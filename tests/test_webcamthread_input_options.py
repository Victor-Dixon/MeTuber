# File: tests/test_webcamthread_input_options.py
import types
from webcam_threading import WebcamThread

class DummyStyle:
    def apply(self, frame, **params): return frame

def test_input_options_exists_and_is_init():
    wt = WebcamThread(
        input_device="video=OBS Virtual Camera",
        style_instance=DummyStyle(),
        style_params={"max_fps": 24, "frame_skip": 1},
    )
    # Must exist and be a dict
    assert hasattr(wt, "input_options")
    assert isinstance(wt.input_options, dict)
    # Should reflect FPS derived from params
    assert wt.input_options.get("framerate") == "24"
    # Can be updated at runtime
    wt.update_params({"max_fps": 15})
    assert wt.input_options.get("framerate") == "15"
