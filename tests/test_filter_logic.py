import os
import sys
import numpy as np
import cv2
import pytest
import importlib
import pkgutil
import inspect
from skimage.metrics import structural_similarity as ssim

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles.base import Style

# Directory to save outputs
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'filter_test_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Dummy test image (colorful gradient)
def get_test_image():
    h, w = 256, 256
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            img[y, x] = [x % 256, y % 256, (x + y) % 256]
    return img

# Dynamic style loader (like main app)
def load_all_styles():
    style_instances = {}
    packages_to_scan = ['styles']
    seen_classes = set()
    for pkg_name in packages_to_scan:
        try:
            package = importlib.import_module(pkg_name)
        except ImportError as e:
            print(f"Error loading package {pkg_name}: {e}")
            continue
        for _, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            if ispkg:
                continue
            try:
                module = importlib.import_module(modname)
                for cls_name in dir(module):
                    cls = getattr(module, cls_name)
                    if (
                        inspect.isclass(cls) and
                        issubclass(cls, Style) and
                        cls is not Style and
                        not inspect.isabstract(cls) and
                        cls not in seen_classes
                    ):
                        if getattr(cls, "__skip_registration__", False):
                            continue
                        try:
                            instance = cls()
                            seen_classes.add(cls)
                            style_instances[instance.name] = instance
                        except Exception as instantiation_error:
                            print(f"Failed to instantiate style '{cls.__name__}': {instantiation_error}")
            except Exception as module_error:
                print(f"Failed to load module '{modname}': {module_error}")
    return style_instances

@pytest.mark.parametrize("style_name,style_instance", list(load_all_styles().items()))
def test_filter_logic(style_name, style_instance):
    img = get_test_image()
    params = {p['name']: p.get('default', 0) for p in getattr(style_instance, 'parameters', [])}
    
    try:
        out = style_instance.apply(img.copy(), params)
        
        # 1. Basic assertions
        assert out is not None, f"{style_name} returned None"
        assert out.shape == img.shape, f"{style_name} output shape mismatch: {out.shape} vs {img.shape}"
        
        # 2. Check for meaningful change (image is not identical)
        if style_name not in ["Original", "Color Effects"]:
            if min(out.shape[:2]) >= 7:
                similarity = ssim(img, out, multichannel=True, channel_axis=2, win_size=7)
                assert similarity < 0.99, f"{style_name} did not change the image significantly (SSIM: {similarity})"
            else:
                print(f"[SKIP] SSIM check for {style_name} due to small image size: {out.shape}")

        # 3. Check for non-blank output (not all black or all white)
        assert np.any(out != 0), f"{style_name} produced a completely black image"
        assert np.any(out != 255), f"{style_name} produced a completely white image"
        
        # 4. Save output for visual inspection
        out_path = os.path.join(OUTPUT_DIR, f"{style_name.replace(' ', '_')}_logic_test.png")
        cv2.imwrite(out_path, out)
        
        print(f"[PASS] {style_name}")
        
    except Exception as e:
        pytest.fail(f"{style_name} crashed: {e}")

if __name__ == "__main__":
    # Run as standalone script
    import pytest
    sys.exit(pytest.main([__file__])) 