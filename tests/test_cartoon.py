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
    for preset in ["Detailed", "Fast", "Advanced", "Anime", "Whole"]:
        result = pro.apply(dummy_image, {"preset": preset})
        assert result.shape == dummy_image.shape
        assert pro.current_variant == preset


def test_cartoon_kwargs_sets_variant(dummy_image):
    pro = CartoonStylePro()
    pro.apply(dummy_image, preset="Anime")
    assert pro.current_variant == "Anime"


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


def test_migrate_params_preserves_unknown_keys():
    pro = CartoonStylePro()
    migrated = pro._migrate_params({
        "bilateral_filter_diameter": 13,
        "custom_edge_gamma": 0.8,
        "color_levels": 16,
    })
    assert migrated["bilateral_d"] == 13
    # ensure mapped values still applied
    assert migrated["bits"] == 4  # 16 levels -> 4 bits
    # unmapped parameter should be preserved verbatim
    assert "custom_edge_gamma" in migrated
    assert migrated["custom_edge_gamma"] == 0.8


def test_cartoon_clamps_and_logs_invalid_params(dummy_image, caplog):
    pro = CartoonStylePro()
    with caplog.at_level("WARNING"):
        params = pro._p({"kmeans_eps": -1, "bilateral_passes": 999}, provided_keys={"kmeans_eps", "bilateral_passes"})
    assert params["kmeans_eps"] >= 1e-6
    assert params["bilateral_passes"] <= 4