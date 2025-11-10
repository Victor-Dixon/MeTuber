#!/usr/bin/env python3
"""
Consolidated Styles Module
Combines similar effects into unified style classes with variant selectors.
This reduces GUI clutter and improves maintainability.
"""

import cv2
import numpy as np
from typing import Dict, Any, List
from ..base import Style
from ..artistic.cartoon import CartoonStylePro


class ConsolidatedCartoon(Style):
    """
    Consolidated Cartoon Effects
    Combines: Cartoon, CartoonStyle, AdvancedCartoon, AdvancedCartoon2, CartoonWholeImage
    """
    name = "Cartoon Effects"
    category = "Artistic"
    variants = ["Classic", "Fast", "Anime", "Advanced", "Whole Image"]
    default_variant = "Fast"

    def __init__(self):
        super().__init__()
        self._pro = CartoonStylePro()

    def define_parameters(self):
        """Define parameters for cartoon effects."""
        return [
            {
                "name": "intensity",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Effect Intensity"
            },
            {
                "name": "preset",
                "type": "str",
                "default": "Fast",
                "options": ["Classic", "Fast", "Anime", "Advanced", "Whole"],
                "label": "Preset"
            }
        ]

    def apply(self, image, params=None):
        if params is None:
            params = {}
        preset_map = {
            "Classic": "Detailed",
            "Fast": "Fast",
            "Anime": "Anime",
            "Advanced": "Advanced",
            "Whole": "Fast",
        }
        preset = preset_map.get(self.current_variant, "Fast")
        pro_params = {"preset": preset}
        return self._pro.apply(image, pro_params)


class ConsolidatedSketch(Style):
    """
    Consolidated Sketch Effects
    Combines: PencilSketch, AdvancedPencilSketch, SketchAndColor, LineArt, Stippling
    """
    name = "Sketch Effects"
    category = "Artistic"
    variants = ["Pencil", "Advanced Pencil", "Color Sketch", "Line Art", "Stippling"]
    default_variant = "Pencil"
    
    def define_parameters(self):
        """Define parameters for sketch effects."""
        return [
            {
                "name": "intensity",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Effect Intensity"
            },
            {
                "name": "detail",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Detail Level"
            },
            {
                "name": "contrast",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Contrast"
            },
            {
                "name": "color_preservation",
                "type": "int",
                "default": 0,
                "min": 0,
                "max": 100,
                "label": "Color Preservation"
            }
        ]
    
    def apply(self, image, params=None):
        """Apply sketch effect based on selected variant."""
        if params is None:
            params = {}
        
        variant = self.current_variant
        intensity = params.get("intensity", 50) / 100.0
        detail = params.get("detail", 50) / 100.0
        contrast = params.get("contrast", 50) / 100.0
        color_preservation = params.get("color_preservation", 0) / 100.0
        
        if variant == "Pencil":
            return self._apply_pencil_sketch(image, intensity, detail, contrast)
        elif variant == "Advanced Pencil":
            return self._apply_advanced_pencil(image, intensity, detail, contrast)
        elif variant == "Color Sketch":
            return self._apply_color_sketch(image, intensity, detail, contrast, color_preservation)
        elif variant == "Line Art":
            return self._apply_line_art(image, intensity, detail, contrast)
        elif variant == "Stippling":
            return self._apply_stippling(image, intensity, detail, contrast)
        else:
            return image
    
    def _apply_pencil_sketch(self, image, intensity, detail, contrast):
        """Basic pencil sketch effect."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Invert and blur
        inverted = 255 - gray
        blur_radius = int(21 * (1 - detail)) + 1
        if blur_radius % 2 == 0:
            blur_radius += 1
        blurred = cv2.GaussianBlur(inverted, (blur_radius, blur_radius), 0)
        
        # Blend
        sketch = cv2.divide(gray, 255 - blurred, scale=256)
        
        # Apply contrast
        sketch = cv2.convertScaleAbs(sketch, alpha=1 + contrast, beta=0)
        
        # Convert back to BGR
        sketch_bgr = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        
        return cv2.addWeighted(image, 1 - intensity, sketch_bgr, intensity, 0)
    
    def _apply_advanced_pencil(self, image, intensity, detail, contrast):
        """Advanced pencil sketch with edge detection."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        edges = cv2.dilate(edges, None)
        
        # Invert and blur
        inverted = 255 - gray
        blur_radius = int(21 * (1 - detail)) + 1
        if blur_radius % 2 == 0:
            blur_radius += 1
        blurred = cv2.GaussianBlur(inverted, (blur_radius, blur_radius), 0)
        
        # Combine
        sketch = cv2.divide(gray, 255 - blurred, scale=256)
        sketch = cv2.bitwise_and(sketch, 255 - edges)
        
        # Apply contrast
        sketch = cv2.convertScaleAbs(sketch, alpha=1 + contrast, beta=0)
        
        # Convert back to BGR
        sketch_bgr = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        
        return cv2.addWeighted(image, 1 - intensity, sketch_bgr, intensity, 0)
    
    def _apply_color_sketch(self, image, intensity, detail, contrast, color_preservation):
        """Color sketch effect."""
        # Apply pencil sketch
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        inverted = 255 - gray
        blur_radius = int(21 * (1 - detail)) + 1
        if blur_radius % 2 == 0:
            blur_radius += 1
        blurred = cv2.GaussianBlur(inverted, (blur_radius, blur_radius), 0)
        sketch = cv2.divide(gray, 255 - blurred, scale=256)
        
        # Apply contrast
        sketch = cv2.convertScaleAbs(sketch, alpha=1 + contrast, beta=0)
        
        # Blend with original colors
        sketch_3d = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
        result = cv2.addWeighted(image, color_preservation, sketch_3d, 1 - color_preservation, 0)
        
        return cv2.addWeighted(image, 1 - intensity, result, intensity, 0)
    
    def _apply_line_art(self, image, intensity, detail, contrast):
        """Line art effect."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Edge detection with adaptive thresholds
        threshold1 = int(50 * detail)
        threshold2 = int(150 * detail)
        edges = cv2.Canny(gray, threshold1, threshold2)
        
        # Dilate edges
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Invert
        line_art = 255 - edges
        
        # Apply contrast
        line_art = cv2.convertScaleAbs(line_art, alpha=1 + contrast, beta=0)
        
        # Convert back to BGR
        line_art_bgr = cv2.cvtColor(line_art, cv2.COLOR_GRAY2BGR)
        
        return cv2.addWeighted(image, 1 - intensity, line_art_bgr, intensity, 0)
    
    def _apply_stippling(self, image, intensity, detail, contrast):
        """Stippling effect."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Create stippling pattern
        height, width = gray.shape
        stipple = np.zeros((height, width), dtype=np.uint8)
        
        # Random dots based on intensity
        num_dots = int((1 - detail) * height * width * 0.01)
        for _ in range(num_dots):
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            if gray[y, x] < 128:
                stipple[y, x] = 255
        
        # Apply contrast
        stipple = cv2.convertScaleAbs(stipple, alpha=1 + contrast, beta=0)
        
        # Convert back to BGR
        stipple_bgr = cv2.cvtColor(stipple, cv2.COLOR_GRAY2BGR)
        
        return cv2.addWeighted(image, 1 - intensity, stipple_bgr, intensity, 0)


class ConsolidatedColor(Style):
    """
    Consolidated Color Effects
    Combines: BrightnessOnly, ContrastOnly, ColorBalance, VibrantColor, SepiaVibrant, BlackWhite, Negative, InvertColors
    """
    name = "Color Effects"
    category = "Adjustments"
    variants = ["Brightness", "Contrast", "Color Balance", "Vibrant", "Sepia", "Black & White", "Negative", "Invert"]
    default_variant = "Brightness"
    
    def define_parameters(self):
        """Define parameters for color effects."""
        return [
            {
                "name": "intensity",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Effect Intensity"
            },
            {
                "name": "red",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Red Channel"
            },
            {
                "name": "green",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Green Channel"
            },
            {
                "name": "blue",
                "type": "int",
                "default": 50,
                "min": 0,
                "max": 100,
                "label": "Blue Channel"
            },
            {
                "name": "vibrance",
                "type": "float",
                "default": 1.5,
                "min": 0.0,
                "max": 3.0,
                "step": 0.1,
            }
        ]
    
    def apply(self, image, params=None):
        """Apply color effect based on selected variant."""
        if params is None:
            params = {}
        
        variant = self.current_variant
        intensity = params.get("intensity", 50) / 100.0
        red = params.get("red", 50) / 100.0
        green = params.get("green", 50) / 100.0
        blue = params.get("blue", 50) / 100.0
        vibrance = params.get("vibrance", 1.5)
        
        if variant == "Brightness":
            return self._apply_brightness(image, intensity)
        elif variant == "Contrast":
            return self._apply_contrast(image, intensity)
        elif variant == "Color Balance":
            return self._apply_color_balance(image, red, green, blue)
        elif variant == "Vibrant":
            return self._apply_vibrant(image, intensity, vibrance)
        elif variant == "Sepia":
            return self._apply_sepia(image, intensity)
        elif variant == "Black & White":
            return self._apply_black_white(image, intensity)
        elif variant == "Negative":
            return self._apply_negative(image, intensity)
        elif variant == "Invert":
            return self._apply_invert(image, intensity)
        else:
            return image
    
    def _apply_brightness(self, image, intensity):
        """Brightness adjustment."""
        brightness = (intensity - 0.5) * 2  # -1 to 1
        return cv2.convertScaleAbs(image, alpha=1, beta=brightness * 50)
    
    def _apply_contrast(self, image, intensity):
        """Contrast adjustment."""
        contrast = 0.5 + intensity  # 0.5 to 1.5
        return cv2.convertScaleAbs(image, alpha=contrast, beta=0)
    
    def _apply_color_balance(self, image, red, green, blue):
        """Color balance adjustment."""
        # Convert to float
        img_float = image.astype(np.float32) / 255.0
        
        # Apply color balance
        img_float[:, :, 0] *= blue   # Blue channel
        img_float[:, :, 1] *= green  # Green channel
        img_float[:, :, 2] *= red    # Red channel
        
        # Clip and convert back
        img_float = np.clip(img_float, 0, 1)
        return (img_float * 255).astype(np.uint8)
    
    def _apply_vibrant(self, image, intensity, vibrance):
        """Vibrant color effect."""
        return cv2.bitwise_not(image)

    def _apply_sepia(self, image, intensity):
        """Sepia color effect."""
        # Sepia matrix
        sepia_matrix = np.array([
            [0.393, 0.769, 0.189],
            [0.349, 0.686, 0.168],
            [0.272, 0.534, 0.131]
        ])
        
        # Apply sepia
        sepia = cv2.transform(image, sepia_matrix)
        sepia = np.clip(sepia, 0, 255).astype(np.uint8)
        
        return cv2.addWeighted(image, 1 - intensity, sepia, intensity, 0)
    
    def _apply_black_white(self, image, intensity):
        """Black and white effect."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(image, 1 - intensity, gray_bgr, intensity, 0)
    
    def _apply_negative(self, image, intensity):
        """Negative effect."""
        negative = 255 - image
        return cv2.addWeighted(image, 1 - intensity, negative, intensity, 0)
    
    def _apply_invert(self, image, intensity):
        """Invert effect."""
        inverted = cv2.bitwise_not(image)
        return cv2.addWeighted(image, 1 - intensity, inverted, intensity, 0) 