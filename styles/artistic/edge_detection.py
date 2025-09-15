import cv2
import numpy as np
from typing import Any, Dict, Optional, List
from ..base import Style

class EdgeDetection(Style):
    """
    Improved edge detection style with multiple variants and enhanced features.
    """
    name = "Edge Detection"
    category = "Artistic"
    variants = ["Standard", "Enhanced", "Color"]
    default_variant = "Standard"

    def define_parameters(self) -> List[Dict[str, Any]]:
        """Define base parameters for edge detection."""
        return [
            {
                "name": "mode",
                "type": "str",
                "default": "Standard",
                "options": ["Standard", "Enhanced", "Color"],
                "label": "Edge Detection Mode"
            },
            {
                "name": "threshold1",
                "type": "int",
                "default": 100,
                "min": 0,
                "max": 500,
                "step": 1,
                "label": "Threshold 1"
            },
            {
                "name": "threshold2",
                "type": "int",
                "default": 200,
                "min": 0,
                "max": 500,
                "step": 1,
                "label": "Threshold 2"
            }
        ]

    def define_variant_parameters(self, variant: str) -> List[Dict[str, Any]]:
        """Define variant-specific parameters."""
        if variant == "Enhanced":
            return [
                {
                    "name": "edge_thickness",
                    "type": "int",
                    "default": 1,
                    "min": 1,
                    "max": 5,
                    "step": 1,
                    "label": "Edge Thickness"
                },
                {
                    "name": "noise_reduction",
                    "type": "float",
                    "default": 1.0,
                    "min": 0.1,
                    "max": 3.0,
                    "step": 0.1,
                    "label": "Noise Reduction"
                }
            ]
        elif variant == "Color":
            return [
                {
                    "name": "edge_color_r",
                    "type": "int",
                    "default": 255,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Edge Color (Red)"
                },
                {
                    "name": "edge_color_g",
                    "type": "int",
                    "default": 255,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Edge Color (Green)"
                },
                {
                    "name": "edge_color_b",
                    "type": "int",
                    "default": 255,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Edge Color (Blue)"
                },
                {
                    "name": "background_color_r",
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Background Color (Red)"
                },
                {
                    "name": "background_color_g",
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Background Color (Green)"
                },
                {
                    "name": "background_color_b",
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "max": 255,
                    "step": 1,
                    "label": "Background Color (Blue)"
                }
            ]
        return []

    def apply(self, image: np.ndarray, params: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Apply edge detection based on selected variant."""
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array")

        # Validate and get parameters
        params = self.validate_params(params or {})
        variant = params.get("mode", self.current_variant)

        # Apply variant-specific processing
        if variant == "Standard":
            return self._apply_standard_edge_detection(image, params)
        elif variant == "Enhanced":
            return self._apply_enhanced_edge_detection(image, params)
        elif variant == "Color":
            return self._apply_color_edge_detection(image, params)
        else:
            raise ValueError(f"Unknown edge detection variant: {variant}")

    def _apply_standard_edge_detection(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply standard Canny edge detection."""
        threshold1 = params.get("threshold1", 100)
        threshold2 = params.get("threshold2", 200)

        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection
        edges = cv2.Canny(gray, threshold1, threshold2)

        # Convert back to BGR for consistency with other styles
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return edges_bgr

    def _apply_enhanced_edge_detection(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply enhanced edge detection with noise reduction and thickness control."""
        threshold1 = params.get("threshold1", 100)
        threshold2 = params.get("threshold2", 200)
        edge_thickness = params.get("edge_thickness", 1)
        noise_reduction = params.get("noise_reduction", 1.0)

        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply noise reduction
        if noise_reduction > 1.0:
            blur_kernel_size = int(noise_reduction * 2) + 1
            gray = cv2.GaussianBlur(gray, (blur_kernel_size, blur_kernel_size), 0)

        # Apply Canny edge detection
        edges = cv2.Canny(gray, threshold1, threshold2)

        # Apply edge thickness
        if edge_thickness > 1:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (edge_thickness, edge_thickness))
            edges = cv2.dilate(edges, kernel)

        # Convert back to BGR
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return edges_bgr

    def _apply_color_edge_detection(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply colored edge detection with custom colors."""
        threshold1 = params.get("threshold1", 100)
        threshold2 = params.get("threshold2", 200)
        edge_color = (
            params.get("edge_color_b", 255),
            params.get("edge_color_g", 255),
            params.get("edge_color_r", 255)
        )
        background_color = (
            params.get("background_color_b", 0),
            params.get("background_color_g", 0),
            params.get("background_color_r", 0)
        )

        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection
        edges = cv2.Canny(gray, threshold1, threshold2)

        # Create colored result
        result = np.full_like(image, background_color, dtype=np.uint8)
        result[edges > 0] = edge_color

        return result
