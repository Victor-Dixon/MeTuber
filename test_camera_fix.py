#!/usr/bin/env python3
"""
Quick test script to verify the Windows camera fix works.
Run this before running the full application.
"""

import os
import sys
import subprocess
import time

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def check_ffmpeg():
    """Check if ffmpeg is available."""
    print_header("1. Checking FFmpeg Installation")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg found: {version}")
            return True
        else:
            print("❌ FFmpeg not working properly")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found in PATH")
        print("   Install from: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"❌ Error checking FFmpeg: {e}")
        return False

def list_dshow_devices():
    """List DirectShow devices."""
    print_header("2. Detecting DirectShow Video Devices")
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stderr if result.stderr else result.stdout
        
        devices = []
        for line in output.split('\n'):
            if '"' in line and '(video)' in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    device_name = parts[1]
                    devices.append(device_name)
                    print(f"  📹 {device_name}")
        
        if not devices:
            print("❌ No video devices found!")
            print("   Check camera connection and Windows Camera privacy settings.")
            return []
        
        return devices
    except Exception as e:
        print(f"❌ Error listing devices: {e}")
        return []

def test_camera_open(device_name):
    """Test if camera can be opened."""
    print_header(f"3. Testing Camera: {device_name}")
    try:
        print("  Attempting 2-second capture...")
        result = subprocess.run(
            ["ffmpeg", "-f", "dshow", "-i", f"video={device_name}", 
             "-t", "2", "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stderr if result.stderr else result.stdout
        
        if "frame=" in output:
            # Extract frame count
            for line in output.split('\n'):
                if 'frame=' in line:
                    print(f"✅ Camera opened successfully!")
                    print(f"   {line.strip()}")
            return True
        else:
            print("❌ Camera failed to open")
            print(f"   Error: {output[-200:]}")  # Last 200 chars
            return False
    except subprocess.TimeoutExpired:
        print("❌ Camera test timed out (10 seconds)")
        return False
    except Exception as e:
        print(f"❌ Error testing camera: {e}")
        return False

def check_python_packages():
    """Check if required packages are installed."""
    print_header("4. Checking Python Packages")
    packages = [
        ('av', 'PyAV'),
        ('cv2', 'OpenCV (cv2)'),
        ('numpy', 'NumPy'),
        ('pyvirtualcam', 'PyVirtualCam'),
        ('PyQt5', 'PyQt5')
    ]
    
    all_ok = True
    for pkg_import, pkg_name in packages:
        try:
            __import__(pkg_import)
            print(f"  ✅ {pkg_name}")
        except ImportError:
            print(f"  ❌ {pkg_name} - NOT INSTALLED")
            all_ok = False
    
    return all_ok

def check_texture_file():
    """Check if texture file exists."""
    print_header("5. Checking Texture File")
    texture_path = os.path.join(os.path.dirname(__file__), 'textures', 'texture.png')
    
    if os.path.exists(texture_path):
        size = os.path.getsize(texture_path)
        print(f"  ✅ Texture file exists: {size} bytes")
        return True
    else:
        print(f"  ❌ Texture file missing: {texture_path}")
        print("     (Will create on first run, or create manually)")
        return False

def check_config():
    """Check config.json device name."""
    print_header("6. Checking config.json")
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if not os.path.exists(config_path):
        print("  ⚠️  config.json not found (will be created on first run)")
        return False
    
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        device = config.get('input_device', 'NOT SET')
        print(f"  Current device: {device}")
        
        if 'video=' in device:
            print("  ⚠️  Device has 'video=' prefix (will be auto-corrected)")
        else:
            print("  ✅ Device name format OK")
        
        return True
    except Exception as e:
        print(f"  ❌ Error reading config: {e}")
        return False

def main():
    print("\n" + "█"*70)
    print("  WINDOWS CAMERA FIX - VERIFICATION TEST")
    print("█"*70)
    print("\nThis script checks if all fixes are working correctly.\n")
    
    results = []
    
    # Run all checks
    results.append(("FFmpeg", check_ffmpeg()))
    
    devices = list_dshow_devices()
    results.append(("Device Detection", len(devices) > 0))
    
    if devices:
        # Test first non-virtual camera
        test_device = None
        for dev in devices:
            if "Virtual Camera" not in dev and "Unity" not in dev:
                test_device = dev
                break
        
        if test_device:
            results.append(("Camera Test", test_camera_open(test_device)))
        else:
            print("\n⚠️  Only virtual cameras found, skipping camera test")
            results.append(("Camera Test", False))
    else:
        results.append(("Camera Test", False))
    
    results.append(("Python Packages", check_python_packages()))
    results.append(("Texture File", check_texture_file()))
    results.append(("Config File", check_config()))
    
    # Summary
    print_header("SUMMARY")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status:10} - {name}")
    
    print(f"\n  Score: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n  🎉 All checks passed! Ready to run the application.")
        print("\n  Next step: python webcam_filter_pyqt5.py")
        return 0
    elif passed >= total - 1:
        print("\n  ⚠️  Minor issues detected, but should still work.")
        print("     Try running the application anyway.")
        return 0
    else:
        print("\n  ❌ Critical issues detected. Fix the above errors first.")
        print("\n  Common fixes:")
        print("     - Install FFmpeg: https://ffmpeg.org/download.html")
        print("     - Install Python packages: pip install -r requirements.txt")
        print("     - Check Windows Camera privacy settings")
        print("     - Close apps using the camera (Teams, Zoom, etc.)")
        return 1

if __name__ == "__main__":
    sys.exit(main())

