# tests/test_consolidated_styles.py
import pytest
import numpy as np
import cv2
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles.artistic.cartoon import CartoonStylePro
from styles.consolidated.consolidated_styles import ConsolidatedCartoon
from src.core.style_manager import StyleManager


@pytest.fixture
def test_image():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :, 0] = np.linspace(0, 255, 100).reshape(1, -1)
    img[:, :, 1] = np.linspace(0, 255, 100).reshape(-1, 1)
    img[:, :, 2] = 128
    return img


@pytest.fixture
def style_manager():
    return StyleManager()


def test_consolidated_cartoon_variants(test_image):
    consolidated = ConsolidatedCartoon()
    expected_variants = ["Classic", "Fast", "Anime", "Advanced", "Whole"]

    for variant in expected_variants:
        assert consolidated.set_variant(variant)
        result = consolidated.apply(test_image)
        assert result.shape == test_image.shape


def test_consolidated_cartoon_uses_presets(monkeypatch, test_image):
    calls = []

    def mock_apply(self, image, params=None, **kwargs):
        calls.append(params or kwargs)
        return image

    monkeypatch.setattr(CartoonStylePro, "apply", mock_apply, raising=False)
    consolidated = ConsolidatedCartoon()
    consolidated.set_variant("Advanced")
    consolidated.apply(test_image)
    assert calls
    assert calls[0]["preset"] == "Advanced"


def test_style_manager_mappings(style_manager):
    mapping = style_manager.get_consolidated_style_mapping()
    assert mapping["cartoon"] == {"style": "Cartoon", "variant": "Detailed"}
    assert mapping["advanced_cartoon"]["variant"] == "Advanced"
    assert mapping["advanced_cartoon2"]["variant"] == "Anime"
    assert mapping["catoonwholeimage"]["variant"] == "Whole"


def test_cartoon_style_pro_variant_parameters():
    pro = CartoonStylePro()
    params = pro.get_variant_parameters("Detailed")
    preset_param = next(p for p in params if p["name"] == "preset")
    assert set(preset_param["options"]) >= {"Detailed", "Fast", "Advanced", "Anime", "Whole"}


def test_cartoon_style_pro_apply_each_preset(test_image):
    pro = CartoonStylePro()
    for preset in ["Detailed", "Fast", "Advanced", "Anime", "Whole"]:
        result = pro.apply(test_image, {"preset": preset})
        assert result.shape == test_image.shape


def test_cartoon_style_pro_clamping_logs(monkeypatch, caplog, test_image):
    pro = CartoonStylePro()
    with caplog.at_level("WARNING"):
        pro.apply(test_image, {"preset": "Advanced", "kmeans_eps": -10})
    assert any("kmeans_eps" in record.message for record in caplog.records) 