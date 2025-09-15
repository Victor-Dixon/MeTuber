# styles/artistic/unified_sketch.py
import cv2
import numpy as np
from typing import Any, Dict, Optional, List
from ..base import Style


class SketchStyle(Style):
    """
    Unified Sketch style that consolidates multiple sketch variants into a single class.
    Supports Pencil, Advanced, and Color modes.
    """

    name = "Sketch"
    category = "Artistic"
    variants = ["Pencil", "Advanced", "Color"]
    default_variant = "Pencil"

    def __init__(self):
        super().__init__()

    def define_parameters(self) -> List[Dict[str, Any]]:
        """Define base parameters for sketch effect."""
        return [
            {
                "name": "mode",
                "type": "str",
                "default": "Pencil",
                "options": ["Pencil", "Advanced", "Color"],
                "label": "Sketch Mode"
            },
            {
                "name": "edge_strength",
                "type": "float",
                "default": 0.5,
                "min": 0.1,
                "max": 1.0,
                "step": 0.1,
                "label": "Edge Strength"
            },
            {
                "name": "detail_level",
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 5,
                "step": 1,
                "label": "Detail Level"
            }
        ]

    def define_variant_parameters(self, variant: str) -> List[Dict[str, Any]]:
        """Define variant-specific parameters."""
        if variant == "Color":
            return [
                {
                    "name": "color_intensity",
                    "type": "float",
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.1,
                    "label": "Color Intensity"
                },
                {
                    "name": "preserve_edges",
                    "type": "bool",
                    "default": True,
                    "label": "Preserve Edges"
                },
                {
                    "name": "saturation_boost",
                    "type": "float",
                    "default": 1.2,
                    "min": 0.5,
                    "max": 2.0,
                    "step": 0.1,
                    "label": "Saturation Boost"
                }
            ]
        elif variant == "Advanced":
            return [
                {
                    "name": "gaussian_blur",
                    "type": "float",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 5.0,
                    "step": 0.1,
                    "label": "Gaussian Blur"
                },
                {
                    "name": "edge_threshold",
                    "type": "int",
                    "default": 100,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Edge Threshold"
                },
                {
                    "name": "contrast_enhancement",
                    "type": "float",
                    "default": 1.5,
                    "min": 0.5,
                    "max": 3.0,
                    "step": 0.1,
                    "label": "Contrast Enhancement"
                }
            ]
        return []

    def apply(self, image: np.ndarray, params: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Apply sketch effect based on selected variant."""
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array")

        # Validate and get parameters
        params = self.validate_params(params or {})
        variant = params.get("mode", self.current_variant)

        # Apply variant-specific processing
        if variant == "Pencil":
            return self._apply_pencil_sketch(image, params)
        elif variant == "Advanced":
            return self._apply_advanced_sketch(image, params)
        elif variant == "Color":
            return self._apply_color_sketch(image, params)
        else:
            raise ValueError(f"Unknown sketch variant: {variant}")

    def _apply_pencil_sketch(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply classic pencil sketch effect."""
        edge_strength = params.get("edge_strength", 0.5)
        detail_level = params.get("detail_level", 3)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate blur intensity based on detail level
        blur_intensity = 15 - (detail_level * 2)  # Higher detail = less blur
        blur_intensity = max(1, blur_intensity)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (blur_intensity, blur_intensity), 0)

        # Apply adaptive threshold
        sketch = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Adjust edge strength
        if edge_strength < 1.0:
            # Reduce edge intensity
            sketch = cv2.convertScaleAbs(sketch, alpha=edge_strength, beta=0)

        return sketch

    def _apply_advanced_sketch(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply advanced sketch effect with enhanced features."""
        edge_strength = params.get("edge_strength", 0.5)
        detail_level = params.get("detail_level", 3)
        gaussian_blur = params.get("gaussian_blur", 1.0)
        edge_threshold = params.get("edge_threshold", 100)
        contrast_enhancement = params.get("contrast_enhancement", 1.5)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blur_kernel_size = int(gaussian_blur * 2) + 1
        blurred = cv2.GaussianBlur(gray, (blur_kernel_size, blur_kernel_size), 0)

        # Apply edge detection
        edges = cv2.Canny(blurred, edge_threshold, edge_threshold * 2)

        # Enhance edges based on detail level
        kernel_size = 2 * detail_level + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        edges = cv2.dilate(edges, kernel)

        # Apply adaptive threshold for sketch effect
        sketch = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Combine edges with sketch
        combined = cv2.bitwise_or(sketch, edges)

        # Adjust contrast
        combined = cv2.convertScaleAbs(combined, alpha=contrast_enhancement, beta=0)

        # Apply edge strength
        if edge_strength < 1.0:
            combined = cv2.convertScaleAbs(combined, alpha=edge_strength, beta=0)

        return combined

    def _apply_color_sketch(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply colored sketch effect."""
        edge_strength = params.get("edge_strength", 0.5)
        detail_level = params.get("detail_level", 3)
        color_intensity = params.get("color_intensity", 0.7)
        preserve_edges = params.get("preserve_edges", True)
        saturation_boost = params.get("saturation_boost", 1.2)

        # Convert to grayscale for sketch
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate blur intensity based on detail level
        blur_intensity = 15 - (detail_level * 2)
        blur_intensity = max(1, blur_intensity)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (blur_intensity, blur_intensity), 0)

        # Create sketch
        sketch = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Convert sketch to 3-channel
        sketch_3ch = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

        # Apply color from original image
        if color_intensity > 0:
            # Boost saturation of original image
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation_boost, 0, 255)
            colored = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # Blend colored image with sketch
            colored_sketch = cv2.addWeighted(
                colored, color_intensity,
                sketch_3ch, 1 - color_intensity, 0
            )
        else:
            colored_sketch = sketch_3ch

        # Add edge detection if preserve_edges is enabled
        if preserve_edges:
            edges = cv2.Canny(gray, 50, 150)
            edges_3ch = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            # Combine edges with colored sketch
            result = cv2.bitwise_or(colored_sketch, edges_3ch)
        else:
            result = colored_sketch

        # Apply edge strength
        if edge_strength < 1.0:
            result = cv2.convertScaleAbs(result, alpha=edge_strength, beta=0)

        return result

    def _create_pencil_texture(self, size: tuple) -> np.ndarray:
        """Create a pencil-like texture overlay."""
        height, width = size
        texture = np.random.rand(height, width) * 0.3 + 0.7
        texture = np.uint8(texture * 255)
        return texture

    def _apply_texture_overlay(self, image: np.ndarray, texture_intensity: float = 0.1) -> np.ndarray:
        """Apply texture overlay to simulate paper/pencil texture."""
        if texture_intensity <= 0:
            return image

        # Create texture
        texture = self._create_pencil_texture(image.shape[:2])
        texture_3ch = cv2.cvtColor(texture, cv2.COLOR_GRAY2BGR)

        # Blend texture with image
        result = cv2.addWeighted(image, 1 - texture_intensity, texture_3ch, texture_intensity, 0)
        return result