#!/usr/bin/env python3
import time
import numpy as np
try:
    import pyvirtualcam
except Exception:
    print("pyvirtualcam not installed.")
    raise

W, H, FPS = 1280, 720, 30
with pyvirtualcam.Camera(width=W, height=H, fps=FPS, backend='obs') as cam:
    print(f"Sending test pattern to {cam.device} @ {W}x{H}@{FPS}")
    t0 = time.time()
    while time.time() - t0 < 5:
        # RGB gradient
        x = np.linspace(0, 255, W, dtype=np.uint8)
        y = np.linspace(0, 255, H, dtype=np.uint8)
        xv, yv = np.meshgrid(x, y)
        frame = np.dstack([xv, yv, np.full_like(xv, 128)])
        cam.send(frame)
        cam.sleep_until_next_frame()
    print("Done.")
