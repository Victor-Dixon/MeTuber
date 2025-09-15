import cv2
import numpy as np
import logging
from ..base import Style

logger = logging.getLogger(__name__)


class AdvancedEdgeDetection(Style):
    """
    A style that applies advanced edge detection with color customization and glow effects.
    Supports Canny, Sobel, and Laplacian methods.
    """
    name = "Advanced Edge Detection"
    category = "Artistic"
    parameters = [
        {
            "name": "method",
            "type": "str",
            "default": "Canny",
            "options": ["Canny", "Sobel", "Laplacian"],
            "label": "Edge Detection Method",
        },
        {
            "name": "threshold1",
            "type": "int",
            "default": 100,
            "min": 0,
            "max": 500,
            "step": 1,
            "label": "Canny Threshold 1",
        },
        {
            "name": "threshold2",
            "type": "int",
            "default": 200,
            "min": 0,
            "max": 500,
            "step": 1,
            "label": "Canny Threshold 2",
        },
        {
            "name": "sobel_ksize",
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 7,
            "step": 2,
            "label": "Sobel Kernel Size",
        },
        {
            "name": "blur",
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 9,
            "step": 2,
            "label": "Pre-Processing Blur",
        },
        {
            "name": "overlay",
            "type": "bool",
            "default": True,
            "label": "Overlay Edges on Image",
        },
        {
            "name": "glow",
            "type": "bool",
            "default": True,
            "label": "Enable Glow Effect",
        },
        {
            "name": "glow_intensity",
            "type": "float",
            "default": 1.0,
            "min": 0.1,
            "max": 3.0,
            "step": 0.1,
            "label": "Glow Intensity",
        },
        {
            "name": "color_mode",
            "type": "str",
            "default": "White",
            "options": ["White", "Red", "Green", "Blue", "Custom"],
            "label": "Edge Color",
        },
        {
            "name": "custom_r",
            "type": "int",
            "default": 255,
            "min": 0,
            "max": 255,
            "step": 5,
            "label": "Custom Red (R)",
        },
        {
            "name": "custom_g",
            "type": "int",
            "default": 255,
            "min": 0,
            "max": 255,
            "step": 5,
            "label": "Custom Green (G)",
        },
        {
            "name": "custom_b",
            "type": "int",
            "default": 255,
            "min": 0,
            "max": 255,
            "step": 5,
            "label": "Custom Blue (B)",
        },
    ]

    def define_parameters(self):
        """
        Returns the parameters for edge detection.
        """
        return self.parameters

    def get_edge_color(self, color_mode, custom_r, custom_g, custom_b):
        """
        Determines the edge color based on the provided color mode and custom RGB values.
        """
        if color_mode == "White":
            return (255, 255, 255)
        elif color_mode == "Red":
            return (0, 0, 255)
        elif color_mode == "Green":
            return (0, 255, 0)
        elif color_mode == "Blue":
            return (255, 0, 0)
        elif color_mode == "Custom":
            # Validate custom values; if invalid, fallback to white.
            if not (0 <= custom_r <= 255 and 0 <= custom_g <= 255 and 0 <= custom_b <= 255):
                return (255, 255, 255)
            # OpenCV uses BGR ordering.
            return (custom_b, custom_g, custom_r)
        else:
            return (255, 255, 255)

    def apply(self, image, params=None):
        """
        Applies advanced edge detection to the input image with customizable parameters.
        """
        # Validate input image
        if image is None:
            raise ValueError("Input image cannot be None.")
        if not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a NumPy array.")
        if len(image.shape) != 3 or image.shape[2] != 3:
            raise ValueError("Input image must be a BGR color image.")

        # Validate and sanitize parameters
        params = self.validate_params(params or {})
        logger.debug("Parameters received: %s", params)

        # Extract parameters
        method = params["method"]
        threshold1 = params["threshold1"]
        threshold2 = params["threshold2"]
        sobel_ksize = params["sobel_ksize"]
        blur_ksize = params["blur"]
        overlay = params["overlay"]
        glow_enabled = params["glow"]
        glow_intensity = params["glow_intensity"]
        color_mode = params["color_mode"]
        custom_r = params["custom_r"]
        custom_g = params["custom_g"]
        custom_b = params["custom_b"]

        # Validate color_mode
        if color_mode not in ["White", "Red", "Green", "Blue", "Custom"]:
            logger.warning("Invalid color_mode detected: %s. Defaulting to White.", color_mode)
            color_mode = "White"
        else:
            logger.debug("Valid color_mode detected: %s.", color_mode)

        # Ensure the blur kernel size is odd
        if blur_ksize % 2 == 0:
            blur_ksize += 1

        # Convert image to grayscale for edge detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        if blur_ksize > 1:
            gray = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)

        # Perform edge detection based on the selected method
        if method == "Canny":
            edges = cv2.Canny(gray, threshold1, threshold2)
        elif method == "Sobel":
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=sobel_ksize)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=sobel_ksize)
            edges = cv2.magnitude(sobelx, sobely)
            edges = cv2.normalize(edges, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        elif method == "Laplacian":
            edges = cv2.Laplacian(gray, cv2.CV_64F, ksize=sobel_ksize)
            edges = cv2.convertScaleAbs(edges)
        else:
            raise ValueError(f"Unknown edge detection method: {method}")

        # Create a binary mask for detected edges
        edge_mask = edges > 0
        logger.debug("Edge mask created. Total edge pixels: %d", np.sum(edge_mask))

        # Initialize a blank image to hold colored edges
        edges_colored = np.zeros_like(image)

        # Retrieve the desired edge color
        edge_color = self.get_edge_color(color_mode, custom_r, custom_g, custom_b)
        logger.debug("Applying edge color: %s", edge_color)

        # Colorize the edges using the mask
        edges_colored[edge_mask] = edge_color

        # Optionally apply a glow effect to the edges
        if glow_enabled:
            glow_kernel = (15, 15)  # This can be dynamic based on image size if desired
            glow = cv2.GaussianBlur(edges_colored, glow_kernel, sigmaX=glow_intensity * 3)
            edges_colored = cv2.addWeighted(edges_colored, 1.0, glow, glow_intensity, 0)
            logger.debug("Glow effect applied.")

        # If overlay is enabled, blend the edge image with the original
        if overlay:
            combined = cv2.addWeighted(image, 0.7, edges_colored, 0.3, 0)
            return combined
        else:
            return edges_colored
