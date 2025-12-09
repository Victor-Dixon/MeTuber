#!/usr/bin/env python3
"""
Test script to verify all required dependencies can be imported.
Run this in your venv to ensure requirements.txt is correct.
"""

import sys

def test_imports():
    """Test all critical imports."""
    errors = []
    
    # Core dependencies
    try:
        import PyQt5
        print("✓ PyQt5 imported successfully")
    except ImportError as e:
        errors.append(f"PyQt5: {e}")
    
    try:
        import cv2
        print(f"✓ opencv-python imported successfully (version: {cv2.__version__})")
    except ImportError as e:
        errors.append(f"opencv-python: {e}")
    
    try:
        import numpy as np
        print(f"✓ numpy imported successfully (version: {np.__version__})")
    except ImportError as e:
        errors.append(f"numpy: {e}")
    
    try:
        import av
        print(f"✓ av (PyAV) imported successfully (version: {av.__version__})")
    except ImportError as e:
        errors.append(f"av: {e}")
    
    try:
        import pyvirtualcam
        print("✓ pyvirtualcam imported successfully")
    except ImportError as e:
        errors.append(f"pyvirtualcam: {e}")
    
    try:
        import psutil
        print("✓ psutil imported successfully")
    except ImportError as e:
        errors.append(f"psutil: {e}")
    
    try:
        import skimage
        print("✓ scikit-image imported successfully")
    except ImportError as e:
        errors.append(f"scikit-image: {e}")
    
    # Application modules
    try:
        from webcam_threading import WebcamThread
        print("✓ webcam_threading imported successfully")
    except ImportError as e:
        errors.append(f"webcam_threading: {e}")
    
    try:
        from styles.base import Style
        print("✓ styles.base imported successfully")
    except ImportError as e:
        errors.append(f"styles.base: {e}")
    
    # Optional dependencies
    try:
        import PIL
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"⚠ Pillow not available (optional): {e}")
    
    try:
        import speech_recognition
        print("✓ SpeechRecognition imported successfully")
    except ImportError as e:
        print(f"⚠ SpeechRecognition not available (optional): {e}")
    
    # Summary
    if errors:
        print("\n❌ Import errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ All critical imports successful!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

