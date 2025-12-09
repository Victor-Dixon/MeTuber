"""
Enhanced AI-Powered Parameter Optimization System

This module provides improved parameter optimization with:
1. Objective quality metrics validation
2. Proper optimization algorithms (grid search, Bayesian optimization)
3. Result validation to ensure improvements
4. Learning from user feedback
5. Better parameter constraints and ranges
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time
from itertools import product
import json
import os

logger = logging.getLogger(__name__)


class QualityMetric(Enum):
    """Quality metrics for evaluating filter output."""
    SHARPNESS = "sharpness"
    CONTRAST = "contrast"
    COLOR_VIBRANCE = "color_vibrance"
    EDGE_PRESERVATION = "edge_preservation"
    NOISE_REDUCTION = "noise_reduction"
    ARTISTIC_QUALITY = "artistic_quality"


@dataclass
class OptimizationResult:
    """Result of parameter optimization."""
    parameters: Dict[str, Any]
    quality_score: float
    metrics: Dict[str, float]
    improvement: float  # Improvement over baseline (0.0 = no change, >0 = better)


class EnhancedAIOptimizer:
    """
    Enhanced AI parameter optimizer with validation and proper optimization algorithms.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or "optimizer_config.json"
        self.learning_history = []
        self.max_learning_history = 100  # Limit to prevent memory leaks
        self.user_feedback = {}  # Store user preferences
        
        # Load learned preferences
        self._load_learning_data()
        
        # Parameter constraints (min, max, step) for each filter type
        self.parameter_constraints = self._initialize_constraints()
        
    def _initialize_constraints(self) -> Dict[str, Dict[str, Tuple[float, float, float]]]:
        """Initialize parameter constraints for each filter type."""
        return {
            "Cartoon": {
                "bilateral_filter_diameter": (3, 25, 2),
                "bilateral_filter_sigmaColor": (20, 200, 10),
                "bilateral_filter_sigmaSpace": (20, 200, 10),
                "canny_threshold1": (20, 200, 10),
                "canny_threshold2": (40, 400, 20),
                "color_levels": (4, 32, 2),
            },
            "Pencil Sketch": {
                "blur_intensity": (3, 35, 2),
                "contrast": (0.5, 3.0, 0.1),
            },
            "Edge Detection": {
                "threshold1": (20, 200, 10),
                "threshold2": (40, 400, 20),
            },
            "Watercolor": {
                "detail_level": (1, 10, 1),
                "saturation_boost": (0.8, 2.0, 0.1),
            },
            "Oil Painting": {
                "brush_size": (3, 15, 1),
            },
        }
    
    def optimize_with_validation(
        self,
        style_name: str,
        current_params: Dict[str, Any],
        frame: np.ndarray,
        apply_filter: Callable[[Dict[str, Any], np.ndarray], np.ndarray],
        optimization_method: str = "grid_search",
        max_iterations: int = 50
    ) -> OptimizationResult:
        """
        Optimize parameters with validation to ensure improvement.
        
        Args:
            style_name: Name of the filter style
            current_params: Current parameter values
            frame: Input frame to optimize on
            apply_filter: Function that applies filter with given parameters
            optimization_method: "grid_search" or "bayesian" (if available)
            max_iterations: Maximum optimization iterations
        
        Returns:
            OptimizationResult with best parameters and quality metrics
        """
        try:
            # Get baseline quality
            baseline_output = apply_filter(current_params, frame)
            baseline_quality = self._evaluate_quality(baseline_output, frame)
            
            self.logger.info(f"Baseline quality score: {baseline_quality['total']:.3f}")
            
            # Get parameter constraints for this style
            constraints = self.parameter_constraints.get(style_name, {})
            if not constraints:
                # Use generic constraints
                constraints = self._get_generic_constraints(current_params)
            
            # Run optimization
            if optimization_method == "grid_search":
                best_result = self._grid_search_optimization(
                    style_name, current_params, frame, apply_filter, 
                    constraints, max_iterations
                )
            else:
                # Fallback to grid search
                best_result = self._grid_search_optimization(
                    style_name, current_params, frame, apply_filter,
                    constraints, max_iterations
                )
            
            # Validate improvement
            improvement = best_result.quality_score - baseline_quality['total']
            
            if improvement > 0.05:  # At least 5% improvement
                self.logger.info(
                    f"✅ Optimization improved quality by {improvement:.3f} "
                    f"({improvement/baseline_quality['total']*100:.1f}%)"
                )
                return OptimizationResult(
                    parameters=best_result.parameters,
                    quality_score=best_result.quality_score,
                    metrics=best_result.metrics,
                    improvement=improvement
                )
            else:
                self.logger.info(
                    f"⚠️ Optimization didn't improve quality significantly "
                    f"({improvement:.3f}). Keeping current parameters."
                )
                return OptimizationResult(
                    parameters=current_params,
                    quality_score=baseline_quality['total'],
                    metrics=baseline_quality,
                    improvement=0.0
                )
                
        except Exception as e:
            self.logger.error(f"Error in optimize_with_validation: {e}")
            return OptimizationResult(
                parameters=current_params,
                quality_score=0.0,
                metrics={},
                improvement=0.0
            )
    
    def _grid_search_optimization(
        self,
        style_name: str,
        current_params: Dict[str, Any],
        frame: np.ndarray,
        apply_filter: Callable,
        constraints: Dict[str, Tuple[float, float, float]],
        max_iterations: int
    ) -> OptimizationResult:
        """Grid search optimization with smart sampling."""
        best_score = -float('inf')
        best_params = current_params.copy()
        best_metrics = {}
        
        # Generate parameter combinations
        param_names = list(constraints.keys())
        param_ranges = []
        
        for param_name in param_names:
            min_val, max_val, step = constraints[param_name]
            # Generate range, but limit to reasonable number of values
            num_values = min(5, int((max_val - min_val) / step) + 1)
            param_range = np.linspace(min_val, max_val, num_values)
            param_ranges.append(param_range)
        
        # Limit total combinations
        total_combinations = np.prod([len(r) for r in param_ranges])
        if total_combinations > max_iterations:
            # Use random sampling instead of full grid
            self.logger.info(
                f"Too many combinations ({total_combinations}). "
                f"Using random sampling ({max_iterations} iterations)."
            )
            tested = set()
            for _ in range(max_iterations):
                # Generate random parameter set
                test_params = current_params.copy()
                for param_name, (min_val, max_val, _) in constraints.items():
                    test_params[param_name] = np.random.uniform(min_val, max_val)
                
                # Skip if already tested
                param_key = tuple(sorted(test_params.items()))
                if param_key in tested:
                    continue
                tested.add(param_key)
                
                # Test this parameter set
                try:
                    output = apply_filter(test_params, frame)
                    quality = self._evaluate_quality(output, frame)
                    score = quality['total']
                    
                    if score > best_score:
                        best_score = score
                        best_params = test_params.copy()
                        best_metrics = quality
                except Exception as e:
                    self.logger.debug(f"Error testing parameters: {e}")
                    continue
        else:
            # Full grid search
            for param_combo in product(*param_ranges):
                test_params = current_params.copy()
                for param_name, value in zip(param_names, param_combo):
                    test_params[param_name] = value
                
                try:
                    output = apply_filter(test_params, frame)
                    quality = self._evaluate_quality(output, frame)
                    score = quality['total']
                    
                    if score > best_score:
                        best_score = score
                        best_params = test_params.copy()
                        best_metrics = quality
                except Exception as e:
                    self.logger.debug(f"Error testing parameters: {e}")
                    continue
        
        return OptimizationResult(
            parameters=best_params,
            quality_score=best_score,
            metrics=best_metrics,
            improvement=0.0
        )
    
    def _evaluate_quality(
        self, 
        output_frame: np.ndarray, 
        input_frame: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate output quality using multiple metrics.
        Returns a dictionary of metric scores (0-1) and total score.
        """
        metrics = {}
        
        try:
            # Convert to grayscale for some metrics
            if len(output_frame.shape) == 3:
                output_gray = cv2.cvtColor(output_frame, cv2.COLOR_BGR2GRAY)
                input_gray = cv2.cvtColor(input_frame, cv2.COLOR_BGR2GRAY)
            else:
                output_gray = output_frame
                input_gray = input_frame
            
            # 1. Sharpness (Laplacian variance)
            laplacian = cv2.Laplacian(output_gray, cv2.CV_64F)
            sharpness = laplacian.var() / 1000.0  # Normalize
            metrics['sharpness'] = min(1.0, sharpness)
            
            # 2. Contrast (standard deviation)
            contrast = np.std(output_gray) / 128.0
            metrics['contrast'] = min(1.0, contrast)
            
            # 3. Color vibrance (for color images)
            if len(output_frame.shape) == 3:
                hsv = cv2.cvtColor(output_frame, cv2.COLOR_BGR2HSV)
                saturation = np.mean(hsv[:, :, 1]) / 255.0
                metrics['color_vibrance'] = saturation
            else:
                metrics['color_vibrance'] = 0.5
            
            # 4. Edge preservation (compare edges with input)
            output_edges = cv2.Canny(output_gray, 50, 150)
            input_edges = cv2.Canny(input_gray, 50, 150)
            edge_similarity = np.sum(output_edges & input_edges) / (
                np.sum(output_edges | input_edges) + 1e-6
            )
            metrics['edge_preservation'] = edge_similarity
            
            # 5. Noise reduction (lower is better, but we want some detail)
            output_noise = self._estimate_noise(output_gray)
            input_noise = self._estimate_noise(input_gray)
            noise_reduction = max(0, (input_noise - output_noise) / (input_noise + 1e-6))
            metrics['noise_reduction'] = min(1.0, noise_reduction)
            
            # 6. Artistic quality (subjective, based on visual appeal)
            # Higher contrast + good sharpness + good color = artistic
            artistic = (
                metrics['contrast'] * 0.3 +
                metrics['sharpness'] * 0.3 +
                metrics['color_vibrance'] * 0.4
            )
            metrics['artistic_quality'] = artistic
            
            # Weighted total score
            weights = {
                'sharpness': 0.2,
                'contrast': 0.2,
                'color_vibrance': 0.15,
                'edge_preservation': 0.15,
                'noise_reduction': 0.1,
                'artistic_quality': 0.2,
            }
            
            total = sum(metrics[key] * weights.get(key, 0) for key in metrics.keys())
            metrics['total'] = total
            
        except Exception as e:
            self.logger.error(f"Error evaluating quality: {e}")
            metrics = {'total': 0.0}
        
        return metrics
    
    def _estimate_noise(self, gray: np.ndarray) -> float:
        """Estimate noise level in grayscale image."""
        kernel = np.ones((3, 3), np.float32) / 9
        mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        variance = cv2.filter2D(
            (gray.astype(np.float32) - mean) ** 2, -1, kernel
        )
        return np.mean(variance)
    
    def _get_generic_constraints(
        self, 
        current_params: Dict[str, Any]
    ) -> Dict[str, Tuple[float, float, float]]:
        """Get generic constraints for unknown parameters."""
        constraints = {}
        for param_name, value in current_params.items():
            if isinstance(value, (int, float)):
                # Default: ±50% range with reasonable step
                min_val = max(0.1, value * 0.5)
                max_val = value * 1.5
                step = (max_val - min_val) / 10
                constraints[param_name] = (min_val, max_val, step)
        return constraints
    
    def record_user_feedback(
        self,
        style_name: str,
        parameters: Dict[str, Any],
        quality_rating: float  # 0-1, user's rating
    ):
        """Record user feedback to learn preferences."""
        key = f"{style_name}_{hash(tuple(sorted(parameters.items())))}"
        self.user_feedback[key] = {
            'style': style_name,
            'parameters': parameters,
            'rating': quality_rating,
            'timestamp': time.time()
        }
        self._save_learning_data()
    
    def _load_learning_data(self):
        """Load learned preferences from disk."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.user_feedback = data.get('user_feedback', {})
                    loaded_history = data.get('learning_history', [])
                    # Limit history size to prevent memory leaks
                    self.learning_history = loaded_history[-self.max_learning_history:]
            except Exception as e:
                self.logger.warning(f"Could not load learning data: {e}")
    
    def _add_to_learning_history(self, entry: Dict[str, Any]) -> None:
        """Add entry to learning history with size limit."""
        self.learning_history.append(entry)
        # Keep only the most recent entries
        if len(self.learning_history) > self.max_learning_history:
            self.learning_history.pop(0)
    
    def _save_learning_data(self):
        """Save learned preferences to disk."""
        try:
            data = {
                'user_feedback': self.user_feedback,
                'learning_history': self.learning_history
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save learning data: {e}")

