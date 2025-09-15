# styles/artistic/unified_cartoon.py
import cv2
import numpy as np
from typing import Any, Dict, Optional, List
from ..base import Style


class CartoonStyle(Style):
    """
    Unified Cartoon style that consolidates multiple cartoon variants into a single class.
    Supports Basic, Advanced, Advanced2, and WholeImage modes.
    """

    name = "Cartoon"
    category = "Artistic"
    variants = ["Basic", "Advanced", "Advanced2", "WholeImage"]
    default_variant = "Basic"

    def __init__(self):
        super().__init__()

    def define_parameters(self) -> List[Dict[str, Any]]:
        """Define base parameters for cartoon effect."""
        return [
            {
                "name": "mode",
                "type": "str",
                "default": "Basic",
                "options": ["Basic", "Advanced", "Advanced2", "WholeImage"],
                "label": "Cartoon Mode"
            },
            {
                "name": "edge_threshold",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 255,
                "step": 1,
                "label": "Edge Threshold"
            },
            {
                "name": "color_saturation",
                "type": "float",
                "default": 1.5,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "label": "Color Saturation"
            },
            {
                "name": "blur_strength",
                "type": "int",
                "default": 5,
                "min": 1,
                "max": 15,
                "step": 1,
                "label": "Blur Strength"
            }
        ]

    def define_variant_parameters(self, variant: str) -> List[Dict[str, Any]]:
        """Define variant-specific parameters."""
        if variant == "Advanced":
            return [
                {
                    "name": "detail_level",
                    "type": "int",
                    "default": 3,
                    "min": 1,
                    "max": 5,
                    "step": 1,
                    "label": "Detail Level"
                },
                {
                    "name": "smoothness",
                    "type": "float",
                    "default": 0.8,
                    "min": 0.1,
                    "max": 1.0,
                    "step": 0.1,
                    "label": "Smoothness"
                },
                {
                    "name": "edge_method",
                    "type": "str",
                    "default": "Canny",
                    "options": ["Canny", "Sobel", "Laplacian"],
                    "label": "Edge Detection Method"
                }
            ]
        elif variant == "Advanced2":
            return [
                {
                    "name": "edge_detection_method",
                    "type": "str",
                    "default": "Canny",
                    "options": ["Canny", "Sobel", "Laplacian"],
                    "label": "Edge Detection Method"
                },
                {
                    "name": "color_quantization",
                    "type": "int",
                    "default": 8,
                    "min": 2,
                    "max": 16,
                    "step": 1,
                    "label": "Color Quantization"
                },
                {
                    "name": "sharpen_intensity",
                    "type": "float",
                    "default": 1.5,
                    "min": 0.0,
                    "max": 3.0,
                    "step": 0.1,
                    "label": "Sharpen Intensity"
                }
            ]
        elif variant == "WholeImage":
            return [
                {
                    "name": "processing_scale",
                    "type": "float",
                    "default": 1.0,
                    "min": 0.5,
                    "max": 2.0,
                    "step": 0.1,
                    "label": "Processing Scale"
                },
                {
                    "name": "preserve_details",
                    "type": "bool",
                    "default": True,
                    "label": "Preserve Details"
                }
            ]
        return []

    def apply(self, image: np.ndarray, params: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """Apply cartoon effect based on selected variant."""
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array")

        # Validate and get parameters
        params = self.validate_params(params or {})
        variant = params.get("mode", self.current_variant)

        # Apply variant-specific processing
        if variant == "Basic":
            return self._apply_basic_cartoon(image, params)
        elif variant == "Advanced":
            return self._apply_advanced_cartoon(image, params)
        elif variant == "Advanced2":
            return self._apply_advanced2_cartoon(image, params)
        elif variant == "WholeImage":
            return self._apply_whole_image_cartoon(image, params)
        else:
            raise ValueError(f"Unknown cartoon variant: {variant}")

    def _apply_basic_cartoon(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply basic cartoon effect."""
        edge_threshold = params.get("edge_threshold", 50)
        color_saturation = params.get("color_saturation", 1.5)
        blur_strength = params.get("blur_strength", 5)

        # Apply bilateral filter for smoothing
        smoothed = cv2.bilateralFilter(image, blur_strength, 75, 75)

        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply edge detection
        edges = cv2.Canny(gray, edge_threshold, edge_threshold * 2)
        edges = cv2.dilate(edges, None)

        # Adjust color saturation
        hsv = cv2.cvtColor(smoothed, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * color_saturation, 0, 255)
        saturated = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        # Combine edges with saturated image
        cartoon = cv2.bitwise_and(saturated, saturated, mask=255 - edges)

        return cartoon

    def _apply_advanced_cartoon(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply advanced cartoon effect."""
        edge_threshold = params.get("edge_threshold", 50)
        detail_level = params.get("detail_level", 3)
        smoothness = params.get("smoothness", 0.8)
        edge_method = params.get("edge_method", "Canny")

        # Apply bilateral filter with adaptive parameters
        blur_diameter = int(9 * smoothness)
        sigma_color = int(75 * smoothness)
        sigma_space = int(75 * smoothness)
        smoothed = cv2.bilateralFilter(image, blur_diameter, sigma_color, sigma_space)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply edge detection based on method
        if edge_method == "Canny":
            edges = cv2.Canny(gray, edge_threshold, edge_threshold * 2)
        elif edge_method == "Sobel":
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobel_x**2 + sobel_y**2)
            edges = np.uint8(edges * 255 / edges.max())
            _, edges = cv2.threshold(edges, edge_threshold, 255, cv2.THRESH_BINARY)
        elif edge_method == "Laplacian":
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            edges = np.uint8(np.absolute(laplacian))
            _, edges = cv2.threshold(edges, edge_threshold, 255, cv2.THRESH_BINARY)

        # Enhance edges based on detail level
        kernel_size = 2 * detail_level + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        edges = cv2.dilate(edges, kernel)

        # Color quantization
        levels = 8
        div = 256 // levels
        quantized = smoothed // div * div + div // 2

        # Combine edges with quantized image
        cartoon = cv2.bitwise_and(quantized, quantized, mask=255 - edges)

        return cartoon

    def _apply_advanced2_cartoon(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply advanced cartoon effect with enhanced features."""
        edge_threshold = params.get("edge_threshold", 50)
        edge_method = params.get("edge_detection_method", "Canny")
        color_quantization = params.get("color_quantization", 8)
        sharpen_intensity = params.get("sharpen_intensity", 1.5)

        # Apply bilateral filter
        smoothed = cv2.bilateralFilter(image, 9, 75, 75)

        # Sharpen the image
        if sharpen_intensity > 0:
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]]) * sharpen_intensity
            smoothed = cv2.filter2D(smoothed, -1, kernel)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply edge detection
        if edge_method == "Canny":
            edges = cv2.Canny(gray, edge_threshold, edge_threshold * 2)
        elif edge_method == "Sobel":
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobel_x**2 + sobel_y**2)
            edges = np.uint8(edges * 255 / edges.max())
            _, edges = cv2.threshold(edges, edge_threshold, 255, cv2.THRESH_BINARY)
        elif edge_method == "Laplacian":
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            edges = np.uint8(np.absolute(laplacian))
            _, edges = cv2.threshold(edges, edge_threshold, 255, cv2.THRESH_BINARY)

        # Enhanced edge processing
        edges = cv2.dilate(edges, None)
        edges = cv2.medianBlur(edges, 3)

        # Advanced color quantization
        div = 256 // color_quantization
        quantized = smoothed // div * div + div // 2

        # Apply color palette
        quantized = self._apply_color_palette(quantized, color_quantization)

        # Combine edges with quantized image
        cartoon = cv2.bitwise_and(quantized, quantized, mask=255 - edges)

        return cartoon

    def _apply_whole_image_cartoon(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply cartoon effect to the whole image with uniform processing."""
        edge_threshold = params.get("edge_threshold", 50)
        processing_scale = params.get("processing_scale", 1.0)
        preserve_details = params.get("preserve_details", True)

        # Scale image for processing
        if processing_scale != 1.0:
            height, width = image.shape[:2]
            new_height = int(height * processing_scale)
            new_width = int(width * processing_scale)
            scaled_image = cv2.resize(image, (new_width, new_height))
        else:
            scaled_image = image.copy()

        # Apply bilateral filter
        if preserve_details:
            smoothed = cv2.bilateralFilter(scaled_image, 9, 50, 50)
        else:
            smoothed = cv2.bilateralFilter(scaled_image, 15, 100, 100)

        # Convert to grayscale
        gray = cv2.cvtColor(scaled_image, cv2.COLOR_BGR2GRAY)

        # Apply edge detection
        edges = cv2.Canny(gray, edge_threshold, edge_threshold * 2)
        edges = cv2.dilate(edges, None)

        # Color quantization
        levels = 8
        div = 256 // levels
        quantized = smoothed // div * div + div // 2

        # Combine edges with quantized image
        cartoon = cv2.bitwise_and(quantized, quantized, mask=255 - edges)

        # Scale back to original size if needed
        if processing_scale != 1.0:
            cartoon = cv2.resize(cartoon, (image.shape[1], image.shape[0]))

        return cartoon

    def _apply_color_palette(self, image: np.ndarray, num_colors: int) -> np.ndarray:
        """Apply a predefined color palette to the image."""
        # Define cartoon color palettes
        palettes = {
            4: [(0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)],
            8: [(0, 0, 0), (36, 36, 36), (73, 73, 73), (109, 109, 109),
                (146, 146, 146), (182, 182, 182), (219, 219, 219), (255, 255, 255)],
            16: [(0, 0, 0), (17, 17, 17), (34, 34, 34), (51, 51, 51),
                 (68, 68, 68), (85, 85, 85), (102, 102, 102), (119, 119, 119),
                 (136, 136, 136), (153, 153, 153), (170, 170, 170), (187, 187, 187),
                 (204, 204, 204), (221, 221, 221), (238, 238, 238), (255, 255, 255)]
        }

        if num_colors not in palettes:
            return image

        palette = palettes[num_colors]
        result = np.zeros_like(image)

        # Apply palette to each pixel
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                pixel = image[i, j]
                # Find closest color in palette
                min_dist = float('inf')
                closest_color = palette[0]
                for color in palette:
                    dist = np.sqrt(np.sum((pixel - color) ** 2))
                    if dist < min_dist:
                        min_dist = dist
                        closest_color = color

                result[i, j] = closest_color

        return result