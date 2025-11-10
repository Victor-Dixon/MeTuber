import pytest
import numpy as np
import cv2
from styles.artistic.cartoon import CartoonStylePro


@pytest.fixture
def dummy_image():
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    return cv2.rectangle(img, (25, 25), (75, 75), (0, 255, 0), -1)


def test_cartoon_default_preset(dummy_image):
    pro = CartoonStylePro()
    result = pro.apply(dummy_image)
    assert result is not None
    assert result.shape == dummy_image.shape


def test_cartoon_presets(dummy_image):
    pro = CartoonStylePro()
    for preset in ["Detailed", "Fast", "Advanced", "Anime"]:
        result = pro.apply(dummy_image, {"preset": preset})
        assert result.shape == dummy_image.shape


def test_cartoon_clamps_invalid_params(dummy_image):
    pro = CartoonStylePro()
    result = pro.apply(dummy_image, {"preset": "Advanced", "kmeans_eps": 0, "bilateral_passes": 99})
    assert result.shape == dummy_image.shape


def test_cartoon_accepts_kwargs(dummy_image):
    pro = CartoonStylePro()
    result = pro.apply(dummy_image, bilateral_passes=2, preset="Fast")
    assert result.shape == dummy_image.shape


def test_cartoon_performance_dummy(dummy_image):
    pro = CartoonStylePro()
    large_image = np.ones((480, 640, 3), dtype=np.uint8) * 255
    result = pro.apply(large_image)
    assert result.shape == large_image.shape
