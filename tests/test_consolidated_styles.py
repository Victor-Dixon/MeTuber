# tests/test_consolidated_styles.py
import pytest
import numpy as np
import cv2
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from styles.base import Style
from styles.artistic.unified_cartoon import CartoonStyle
from styles.artistic.unified_sketch import SketchStyle
from styles.color_filters.unified_invert import InvertStyle
from src.core.style_manager import StyleManager
from styles.artistic.unified_cartoon_pro import CartoonStylePro


class TestConsolidatedStyles:
    """Test the new consolidated style system with variant support."""
    
    @pytest.fixture
    def test_image(self):
        """Create a test image for style testing."""
        # Create a colorful test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :, 0] = np.linspace(0, 255, 100).reshape(1, -1)  # Blue gradient
        img[:, :, 1] = np.linspace(0, 255, 100).reshape(-1, 1)  # Green gradient
        img[:, :, 2] = 128  # Red constant
        return img
    
    @pytest.fixture
    def style_manager(self):
        """Create a style manager instance."""
        return StyleManager()

    def test_cartoon_style_variants(self, test_image):
        """Test Cartoon style with all variants."""
        cartoon = CartoonStyle()
        
        # Test all variants
        variants = ["Basic", "Advanced", "Advanced2", "WholeImage"]
        
        for variant in variants:
            # Set variant
            assert cartoon.set_variant(variant)
            assert cartoon.get_current_variant() == variant
            
            # Get parameters for this variant
            params = cartoon.get_variant_parameters(variant)
            assert len(params) > 0
            
            # Check that mode parameter is included
            mode_param = next((p for p in params if p['name'] == 'mode'), None)
            assert mode_param is not None
            assert variant in mode_param['options']
            
            # Test applying the style
            result = cartoon.apply(test_image, {"mode": variant})
            assert result is not None
            assert result.shape == test_image.shape
            assert result.dtype == test_image.dtype

    def test_sketch_style_variants(self, test_image):
        """Test Sketch style with all variants."""
        sketch = SketchStyle()
        
        # Test all variants
        variants = ["Pencil", "Advanced", "Color"]
        
        for variant in variants:
            # Set variant
            assert sketch.set_variant(variant)
            assert sketch.get_current_variant() == variant
            
            # Get parameters for this variant
            params = sketch.get_variant_parameters(variant)
            assert len(params) > 0
            
            # Test applying the style
            result = sketch.apply(test_image, {"mode": variant})
            assert result is not None
            # Sketch styles may return grayscale (2D) or color (3D) images
            assert result.shape[:2] == test_image.shape[:2]  # Same height/width
            assert result.dtype == test_image.dtype

    def test_invert_style_variants(self, test_image):
        """Test Invert style with all variants."""
        invert = InvertStyle()
        
        # Test all variants
        variants = ["Colors", "Filter", "Negative"]
        
        for variant in variants:
            # Set variant
            assert invert.set_variant(variant)
            assert invert.get_current_variant() == variant
            
            # Get parameters for this variant
            params = invert.get_variant_parameters(variant)
            assert len(params) > 0
            
            # Test applying the style
            result = invert.apply(test_image, {"mode": variant})
            assert result is not None
            assert result.shape == test_image.shape
            assert result.dtype == test_image.dtype

    def test_style_manager_variant_support(self, style_manager):
        """Test style manager's variant support."""
        # Test getting styles with variants
        styles_with_variants = style_manager.get_styles_with_variants()
        assert isinstance(styles_with_variants, dict)
        
        # Test getting variants for specific styles
        cartoon_variants = style_manager.get_style_variants("Cartoon")
        assert isinstance(cartoon_variants, list)
        assert len(cartoon_variants) > 0
        
        sketch_variants = style_manager.get_style_variants("Sketch")
        assert isinstance(sketch_variants, list)
        assert len(sketch_variants) > 0
        
        invert_variants = style_manager.get_style_variants("Invert")
        assert isinstance(invert_variants, list)
        assert len(invert_variants) > 0

    def test_style_parameter_validation(self, test_image):
        """Test parameter validation for consolidated styles."""
        cartoon = CartoonStyle()
        
        # Test valid parameters
        valid_params = {
            "mode": "Basic",
            "edge_threshold": 50,
            "color_saturation": 1.5,
            "blur_strength": 5
        }
        
        validated = cartoon.validate_params(valid_params)
        assert validated["mode"] == "Basic"
        assert validated["edge_threshold"] == 50
        
        # Test invalid parameters (should be clamped to valid range)
        invalid_params = {
            "mode": "Basic",
            "edge_threshold": 300,  # Above max
            "color_saturation": 5.0,  # Above max
            "blur_strength": 0  # Below min
        }
        
        # The validation should clamp values instead of raising errors
        validated = cartoon.validate_params(invalid_params)
        assert validated["edge_threshold"] <= 255  # Should be clamped
        assert validated["color_saturation"] <= 3.0  # Should be clamped
        assert validated["blur_strength"] >= 1  # Should be clamped

    def test_style_migration_mapping(self, style_manager):
        """Test migration mapping from old style names to new consolidated styles."""
        mapping = style_manager.get_consolidated_style_mapping()
        
        # Test cartoon migrations
        assert mapping["cartoon"]["style"] == "Cartoon"
        assert mapping["cartoon"]["variant"] == "Detailed"

        assert mapping["advanced_cartoon"]["style"] == "Cartoon"
        assert mapping["advanced_cartoon"]["variant"] == "Advanced"
        assert mapping["advanced_cartoon2"]["variant"] == "Anime"
        
        # Test sketch migrations
        assert mapping["pencil_sketch"]["style"] == "Sketch"
        assert mapping["pencil_sketch"]["variant"] == "Pencil"
        
        # Test invert migrations
        assert mapping["invert_colors"]["style"] == "Invert"
        assert mapping["invert_colors"]["variant"] == "Colors"

    def test_style_complexity_detection(self, style_manager):
        """Test style complexity detection for performance optimization."""
        # Test complexity detection for different styles
        cartoon_complexity = style_manager.get_style_complexity("Cartoon", "Detailed")
        assert cartoon_complexity in ["low", "medium", "high"]
        
        advanced_cartoon_complexity = style_manager.get_style_complexity("Cartoon", "Advanced")
        assert advanced_cartoon_complexity in ["low", "medium", "high"]
        
        # Advanced variants should generally be more complex
        if cartoon_complexity != "high":
            assert advanced_cartoon_complexity in ["medium", "high"]

    def test_variant_parameter_differences(self):
        """CartoonStylePro exposes presets via a preset parameter."""
        cartoon = CartoonStylePro()
        params = cartoon.get_variant_parameters("Detailed")
        preset_param = next(p for p in params if p["name"] == "preset")
        assert set(preset_param["options"]) >= {"Detailed", "Fast", "Advanced", "Anime", "Whole"}

    def test_style_info_completeness(self):
        """Test that style info includes all necessary information."""
        cartoon = CartoonStyle()
        info = cartoon.get_style_info()
        
        assert "name" in info
        assert "category" in info
        assert "variants" in info
        assert "current_variant" in info
        assert "parameters" in info
        assert "description" in info
        
        assert info["name"] == "Cartoon"
        assert info["category"] == "Artistic"
        assert len(info["variants"]) > 0
        assert info["current_variant"] in info["variants"]

    def test_error_handling(self, test_image):
        """Test error handling for invalid variants and parameters."""
        cartoon = CartoonStyle()
        
        # Test invalid variant
        assert not cartoon.set_variant("InvalidVariant")
        
        # Test invalid parameters (should clamp values instead of raising errors)
        invalid_params = {"mode": "InvalidVariant"}
        # This should clamp to default instead of raising error
        validated = cartoon.validate_params(invalid_params)
        assert validated["mode"] == "Basic"  # Should be clamped to default
        
        # Test that applying with invalid params still works (clamped to defaults)
        result = cartoon.apply(test_image, invalid_params)
        assert result is not None
        assert result.shape == test_image.shape
        
        # Test None image
        with pytest.raises(ValueError):
            cartoon.apply(None)

    def test_performance_consistency(self, test_image):
        """Test that style application is consistent across multiple calls."""
        cartoon = CartoonStyle()
        cartoon.set_variant("Basic")
        
        # Apply style multiple times with same parameters
        params = {"mode": "Basic", "edge_threshold": 50}
        
        result1 = cartoon.apply(test_image, params)
        result2 = cartoon.apply(test_image, params)
        
        # Results should be identical
        assert np.array_equal(result1, result2)


if __name__ == "__main__":
    pytest.main([__file__]) 