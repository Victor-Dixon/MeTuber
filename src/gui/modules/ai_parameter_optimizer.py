"""
AI-Powered Automatic Parameter Selection System

This module provides intelligent parameter optimization for video effects
by analyzing video content and automatically selecting optimal parameters.
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import threading
import time

class ContentType(Enum):
    """Types of video content for parameter optimization."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    LOW_LIGHT = "low_light"
    HIGH_CONTRAST = "high_contrast"
    MOTION = "motion"
    STATIC = "static"
    DETAILED = "detailed"
    SIMPLE = "simple"

@dataclass
class ContentAnalysis:
    """Results of content analysis for parameter optimization."""
    content_type: ContentType
    brightness_level: float  # 0.0 to 1.0
    contrast_level: float   # 0.0 to 1.0
    motion_level: float     # 0.0 to 1.0
    detail_level: float     # 0.0 to 1.0
    color_saturation: float # 0.0 to 1.0
    edge_density: float     # 0.0 to 1.0
    noise_level: float      # 0.0 to 1.0

class AIParameterOptimizer:
    """AI-powered parameter optimization for video effects."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analysis_history = []
        self.optimization_cache = {}
        self.is_analyzing = False
        self.analysis_thread = None
        
        # Pre-defined parameter optimization rules
        self.optimization_rules = {
            "Cartoon": self._optimize_cartoon_parameters,
            "Cartoon (Detailed)": self._optimize_cartoon_parameters,
            "Pencil Sketch": self._optimize_sketch_parameters,
            "Edge Detection": self._optimize_edge_detection_parameters,
            "Watercolor": self._optimize_watercolor_parameters,
            "Oil Painting": self._optimize_oil_painting_parameters,
        }
    
    def analyze_frame(self, frame: np.ndarray) -> ContentAnalysis:
        """Analyze a video frame to determine content characteristics."""
        try:
            if frame is None or frame.size == 0:
                return self._get_default_analysis()
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Analyze brightness
            brightness = np.mean(gray) / 255.0
            
            # Analyze contrast
            contrast = np.std(gray) / 255.0
            
            # Analyze motion (compare with previous frame)
            motion_level = self._analyze_motion(gray)
            
            # Analyze detail level using edge detection
            detail_level = self._analyze_detail(gray)
            
            # Analyze color saturation
            saturation = self._analyze_saturation(frame)
            
            # Analyze edge density
            edge_density = self._analyze_edge_density(gray)
            
            # Analyze noise level
            noise_level = self._analyze_noise(gray)
            
            # Determine content type
            content_type = self._classify_content(
                brightness, contrast, motion_level, detail_level, saturation
            )
            
            analysis = ContentAnalysis(
                content_type=content_type,
                brightness_level=brightness,
                contrast_level=contrast,
                motion_level=motion_level,
                detail_level=detail_level,
                color_saturation=saturation,
                edge_density=edge_density,
                noise_level=noise_level
            )
            
            # Store in history for temporal analysis
            self.analysis_history.append(analysis)
            if len(self.analysis_history) > 30:  # Keep last 30 frames
                self.analysis_history.pop(0)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing frame: {e}")
            return self._get_default_analysis()
    
    def optimize_parameters(self, style_name: str, current_params: Dict[str, Any], 
                          analysis: ContentAnalysis) -> Dict[str, Any]:
        """Optimize parameters based on content analysis."""
        try:
            # Check if we have optimization rules for this style
            if style_name in self.optimization_rules:
                optimized_params = self.optimization_rules[style_name](current_params, analysis)
                self.logger.info(f"🤖 AI optimized parameters for {style_name}: {optimized_params}")
                return optimized_params
            else:
                # Use generic optimization
                return self._generic_parameter_optimization(current_params, analysis)
                
        except Exception as e:
            self.logger.error(f"Error optimizing parameters: {e}")
            return current_params
    
    def _optimize_cartoon_parameters(self, current_params: Dict[str, Any], 
                                   analysis: ContentAnalysis) -> Dict[str, Any]:
        """Optimize Cartoon effect parameters based on content analysis."""
        optimized = current_params.copy()
        
        # Adjust bilateral filter parameters based on detail level
        if analysis.detail_level > 0.7:
            # High detail content - use finer filtering
            optimized['bilateral_filter_diameter'] = max(3, int(15 * analysis.detail_level))
            optimized['bilateral_filter_sigmaColor'] = max(20, int(100 * analysis.detail_level))
            optimized['bilateral_filter_sigmaSpace'] = max(20, int(100 * analysis.detail_level))
        elif analysis.detail_level < 0.3:
            # Low detail content - use coarser filtering
            optimized['bilateral_filter_diameter'] = max(5, int(25 * (1 - analysis.detail_level)))
            optimized['bilateral_filter_sigmaColor'] = max(30, int(150 * (1 - analysis.detail_level)))
            optimized['bilateral_filter_sigmaSpace'] = max(30, int(150 * (1 - analysis.detail_level)))
        
        # Adjust edge detection based on edge density
        if analysis.edge_density > 0.6:
            # High edge density - use higher thresholds
            optimized['canny_threshold1'] = max(50, int(200 * analysis.edge_density))
            optimized['canny_threshold2'] = max(100, int(400 * analysis.edge_density))
        elif analysis.edge_density < 0.2:
            # Low edge density - use lower thresholds
            optimized['canny_threshold1'] = max(20, int(50 * analysis.edge_density))
            optimized['canny_threshold2'] = max(40, int(100 * analysis.edge_density))
        
        # Adjust color levels based on saturation
        if analysis.color_saturation > 0.7:
            optimized['color_levels'] = max(8, int(20 * analysis.color_saturation))
        else:
            optimized['color_levels'] = max(4, int(12 * analysis.color_saturation))
        
        return optimized
    
    def _optimize_sketch_parameters(self, current_params: Dict[str, Any], 
                                  analysis: ContentAnalysis) -> Dict[str, Any]:
        """Optimize Pencil Sketch parameters based on content analysis."""
        optimized = current_params.copy()
        
        # Adjust blur intensity based on detail level
        if analysis.detail_level > 0.7:
            optimized['blur_intensity'] = max(5, int(25 * analysis.detail_level))
        else:
            optimized['blur_intensity'] = max(10, int(35 * (1 - analysis.detail_level)))
        
        # Adjust contrast based on original contrast
        if analysis.contrast_level > 0.6:
            optimized['contrast'] = max(1.2, 2.5 * analysis.contrast_level)
        else:
            optimized['contrast'] = max(1.0, 1.8 * analysis.contrast_level)
        
        return optimized
    
    def _optimize_edge_detection_parameters(self, current_params: Dict[str, Any], 
                                         analysis: ContentAnalysis) -> Dict[str, Any]:
        """Optimize Edge Detection parameters based on content analysis."""
        optimized = current_params.copy()
        
        # Adjust thresholds based on edge density
        if analysis.edge_density > 0.6:
            optimized['threshold1'] = max(50, int(200 * analysis.edge_density))
            optimized['threshold2'] = max(100, int(400 * analysis.edge_density))
        else:
            optimized['threshold1'] = max(20, int(80 * analysis.edge_density))
            optimized['threshold2'] = max(40, int(160 * analysis.edge_density))
        
        return optimized
    
    def _optimize_watercolor_parameters(self, current_params: Dict[str, Any], 
                                     analysis: ContentAnalysis) -> Dict[str, Any]:
        """Optimize Watercolor parameters based on content analysis."""
        optimized = current_params.copy()
        
        # Adjust parameters based on detail and saturation
        if analysis.detail_level > 0.7:
            optimized['detail_level'] = max(3, int(8 * analysis.detail_level))
        else:
            optimized['detail_level'] = max(1, int(5 * analysis.detail_level))
        
        if analysis.color_saturation > 0.6:
            optimized['saturation_boost'] = max(1.2, 1.8 * analysis.color_saturation)
        else:
            optimized['saturation_boost'] = max(1.0, 1.4 * analysis.color_saturation)
        
        return optimized
    
    def _optimize_oil_painting_parameters(self, current_params: Dict[str, Any], 
                                       analysis: ContentAnalysis) -> Dict[str, Any]:
        """Optimize Oil Painting parameters based on content analysis."""
        optimized = current_params.copy()
        
        # Adjust brush size based on detail level
        if analysis.detail_level > 0.7:
            optimized['brush_size'] = max(3, int(8 * analysis.detail_level))
        else:
            optimized['brush_size'] = max(5, int(12 * (1 - analysis.detail_level)))
        
        return optimized
    
    def _generic_parameter_optimization(self, current_params: Dict[str, Any], 
                                     analysis: ContentAnalysis) -> Dict[str, Any]:
        """Generic parameter optimization for unknown styles."""
        optimized = current_params.copy()
        
        # Generic brightness/contrast adjustments
        if 'brightness' in optimized:
            if analysis.brightness_level < 0.4:
                optimized['brightness'] = min(1.5, 1.0 + (0.4 - analysis.brightness_level))
            elif analysis.brightness_level > 0.8:
                optimized['brightness'] = max(0.7, 1.0 - (analysis.brightness_level - 0.8))
        
        if 'contrast' in optimized:
            if analysis.contrast_level < 0.3:
                optimized['contrast'] = min(2.0, 1.0 + (0.3 - analysis.contrast_level))
            elif analysis.contrast_level > 0.7:
                optimized['contrast'] = max(0.8, 1.0 - (analysis.contrast_level - 0.7))
        
        return optimized
    
    def _analyze_motion(self, gray: np.ndarray) -> float:
        """Analyze motion level between frames."""
        if len(self.analysis_history) < 2:
            return 0.0
        
        # Compare with previous frame
        prev_analysis = self.analysis_history[-2] if self.analysis_history else None
        if prev_analysis is None:
            return 0.0
        
        # For now, return a simple motion estimate based on frame variance
        # This avoids the OpenCV absdiff issue
        motion_level = np.std(gray) / 255.0
        return min(1.0, motion_level * 5)  # Scale up for better sensitivity
    
    def _analyze_detail(self, gray: np.ndarray) -> float:
        """Analyze detail level using edge detection."""
        edges = cv2.Canny(gray, 50, 150)
        detail_level = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        return min(1.0, detail_level * 100)  # Scale up for better sensitivity
    
    def _analyze_saturation(self, frame: np.ndarray) -> float:
        """Analyze color saturation."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1]) / 255.0
        return saturation
    
    def _analyze_edge_density(self, gray: np.ndarray) -> float:
        """Analyze edge density."""
        edges = cv2.Canny(gray, 30, 100)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        return min(1.0, edge_density * 50)  # Scale up for better sensitivity
    
    def _analyze_noise(self, gray: np.ndarray) -> float:
        """Analyze noise level using variance."""
        # Calculate local variance as noise indicator
        kernel = np.ones((3, 3), np.float32) / 9
        mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        variance = cv2.filter2D((gray.astype(np.float32) - mean) ** 2, -1, kernel)
        noise_level = np.mean(variance) / 255.0
        return min(1.0, noise_level * 10)  # Scale up for better sensitivity
    
    def _classify_content(self, brightness: float, contrast: float, motion: float, 
                         detail: float, saturation: float) -> ContentType:
        """Classify content type based on analysis."""
        if brightness < 0.3:
            return ContentType.LOW_LIGHT
        elif contrast > 0.6:
            return ContentType.HIGH_CONTRAST
        elif motion > 0.3:
            return ContentType.MOTION
        elif detail > 0.7:
            return ContentType.DETAILED
        elif detail < 0.3:
            return ContentType.SIMPLE
        elif saturation > 0.7:
            return ContentType.PORTRAIT
        else:
            return ContentType.LANDSCAPE
    
    def _get_default_analysis(self) -> ContentAnalysis:
        """Get default analysis when frame analysis fails."""
        return ContentAnalysis(
            content_type=ContentType.SIMPLE,
            brightness_level=0.5,
            contrast_level=0.5,
            motion_level=0.0,
            detail_level=0.5,
            color_saturation=0.5,
            edge_density=0.5,
            noise_level=0.5
        )
    
    def start_continuous_optimization(self, webcam_service, parameter_manager):
        """Start continuous parameter optimization in background."""
        if self.is_analyzing:
            return
        
        self.is_analyzing = True
        self.analysis_thread = threading.Thread(
            target=self._optimization_loop,
            args=(webcam_service, parameter_manager),
            daemon=True
        )
        self.analysis_thread.start()
        self.logger.info("🤖 AI parameter optimization started")
    
    def stop_continuous_optimization(self):
        """Stop continuous parameter optimization."""
        self.is_analyzing = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=1.0)
        self.logger.info("🤖 AI parameter optimization stopped")
    
    def _optimization_loop(self, webcam_service, parameter_manager):
        """Main optimization loop running in background."""
        while self.is_analyzing:
            try:
                # Get current frame
                if hasattr(webcam_service, 'get_current_frame'):
                    frame = webcam_service.get_current_frame()
                    if frame is not None:
                        # Analyze frame
                        analysis = self.analyze_frame(frame)
                        
                        # Get current style and parameters
                        if hasattr(parameter_manager, 'current_filter_name') and parameter_manager.current_filter_name:
                            style_name = parameter_manager.current_filter_name
                            current_params = parameter_manager.current_embedded_params.copy()
                            
                            # Optimize parameters
                            optimized_params = self.optimize_parameters(style_name, current_params, analysis)
                            
                            # Apply optimized parameters if they're significantly different
                            if self._parameters_changed_significantly(current_params, optimized_params):
                                parameter_manager.current_embedded_params.update(optimized_params)
                                parameter_manager.apply_embedded_effect(style_name, optimized_params)
                                self.logger.info(f"🤖 Applied AI-optimized parameters: {optimized_params}")
                
                time.sleep(2.0)  # Check every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def _parameters_changed_significantly(self, old_params: Dict[str, Any], 
                                       new_params: Dict[str, Any], 
                                       threshold: float = 0.1) -> bool:
        """Check if parameters changed significantly enough to warrant update."""
        if not old_params or not new_params:
            return True
        
        for key in new_params:
            if key in old_params:
                old_val = float(old_params[key])
                new_val = float(new_params[key])
                if abs(new_val - old_val) / max(old_val, 1.0) > threshold:
                    return True
        
        return False 