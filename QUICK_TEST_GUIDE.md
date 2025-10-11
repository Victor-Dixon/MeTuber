# Quick Test Guide - Windows Camera Fix

## What Was Fixed

1. ✅ **Camera I/O Error** - Auto-detects correct DirectShow device name
2. ✅ **Stippling Warnings** - Fixed validation for styles without variants
3. ✅ **Texture Warnings** - Created placeholder texture and improved handling

## Your Actual Camera

According to DirectShow, your camera is named: **`C270 HD WEBCAM`**

Available video devices:
- `C270 HD WEBCAM` (your physical camera)
- `OBS Virtual Camera` (output only)
- `Unity Video Capture` (for OBS ingestion)

## Quick Test Steps

### 1. Close Camera-Using Apps
```powershell
# Close these if running:
# - Microsoft Teams
# - Zoom
# - Discord
# - OBS Studio
# - Chrome/Firefox tabs using camera
```

### 2. Run the Application
```powershell
cd D:\MeTuber
python webcam_filter_pyqt5.py
```

### 3. Expected Output (Clean Start)
```
2025-10-11 XX:XX:XX,XXX - WARNING - sipPyTypeDict() is deprecated...  # ← Safe to ignore (PyQt5 internal)
2025-10-11 XX:XX:XX,XXX - INFO - Loaded style: Original (Category: Basic)
2025-10-11 XX:XX:XX,XXX - INFO - Loaded style: Advanced Cartoon (Category: Favorites)
...
# No other warnings!
```

### 4. Click "Start Virtual Camera"

**Expected Result**:
```
Status: WebcamThread started.
Attempt 1: Opening device via PyAV: device=video=C270 HD WEBCAM format=dshow ...
Successfully opened camera: video=C270 HD WEBCAM
Status: Virtual camera ready: 1280x720 @ 30fps
```

### 5. Check Preview Window
- ✅ Preview label shows live camera feed
- ✅ Applied style visible in preview
- ✅ No error dialogs
- ✅ FPS counter updating

## If Camera Still Doesn't Open

### Check Windows Camera Privacy
1. Windows Settings → **Privacy & Security** → **Camera**
2. Enable "**Camera access**" (system-wide)
3. Enable "**Let desktop apps access camera**"

### Verify Camera Works
```powershell
# Open Windows Camera app
start microsoft.windows.camera:
```

If Windows Camera doesn't work, the issue is at the OS/driver level.

### Check Device Manager
1. Windows Key + X → Device Manager
2. Expand "**Cameras**" or "**Imaging devices**"
3. Look for `C270 HD WEBCAM`
4. Right-click → **Update driver** if yellow warning icon present

### Manual Camera Test
```powershell
# 5-second test capture (should show frame count and fps)
ffmpeg -f dshow -i video="C270 HD WEBCAM" -t 5 -f null -
```

**Expected**: Shows "frame=150" (or similar) with no errors.

## Advanced Troubleshooting

### See Detailed Logs
Check `webcam_app.log` in the MeTuber directory for full error details.

### Test Different Resolution
Edit `config.json`:
```json
"virtual_camera": {
    "width": 640,   // Lower resolution
    "height": 480,
    "fps": 30
}
```

### Force OpenCV Fallback
If PyAV continues to fail, the code includes OpenCV as fallback. The auto-detection will try that automatically.

## Success Indicators

✅ Console shows no warnings (except PyQt5 deprecation)
✅ Preview shows live camera feed with style applied
✅ Status label shows "Running"
✅ Stop button is enabled
✅ No error dialogs appear

## Next Steps After Success

1. **Try different styles** from the tabs
2. **Adjust parameters** with sliders (updates live)
3. **Take snapshots** to test capture
4. **Enable virtual camera output** for Zoom/Teams/Meet

---

**Note**: The fixes made the app auto-detect the correct device name, so even if you have the wrong name in config, it will find "C270 HD WEBCAM" automatically by matching partial names.

