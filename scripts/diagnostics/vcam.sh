#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from src.video.webcam_threading import WebcamThread
import time
wt = WebcamThread(device="video=OBS Virtual Camera", fps=15)
wt.start()
print("Started webcam thread...")
time.sleep(3)
print("Stop reason (so far):", wt.stopped_reason)
wt.stop()
wt.join()
print("Final reason:", wt.stopped_reason)
PY
