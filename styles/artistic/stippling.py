import cv2
import numpy as np
from styles.base import Style

class Stippling(Style):
    """
    A style that applies a stippled effect to the image.
    """
    name = "Stippling"
    category = "Artistic"
    variants = []
    current_variant = None  # explicit for base-class helpers
    parameters = [
        {
            "name": "dot_density",
            "type": "int",
            "default": 10,
            "min": 1,
            "max": 50,
            "step": 1,
            "label": "Dot Density"
        },
        {
            "name": "contrast_adjustment",
            "type": "float",
            "default": 1.0,
            "min": 0.5,
            "max": 3.0,
            "step": 0.1,
            "label": "Contrast Adjustment"
        }
    ]

    def __init__(self):
        super().__init__()
        # Initialize default_params from parameters
        self.default_params = {param["name"]: param["default"] for param in self.parameters}
        # Explicitly ensure variant attribute exists (style has no variants)
        if not hasattr(self, "current_variant"):
            self.current_variant = None

    def define_parameters(self):
        """
        Returns the parameters for the Stippling style.
        """
        return self.parameters

    def apply(self, image, params: dict) -> np.ndarray:
        """
        Apply stippling effect to the image.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply stippling effect
        stippled = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return cv2.cvtColor(stippled, cv2.COLOR_GRAY2BGR)
