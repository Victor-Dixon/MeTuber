# styles/base.py
from typing import List, Dict, Optional, Any, Tuple, Set
from abc import ABC, abstractmethod
import numpy as np
import logging


_logger = logging.getLogger(__name__)
_MISSING_STEP_WARNINGS: Set[Tuple[type, str]] = set()


class Style(ABC):
    """
    Abstract base class for all styles with variant/mode support.
    """
    name = "BaseStyle"
    category = "Base"
    variants = []  # List of available variants/modes
    default_variant = None  # Default variant to use

    def __init__(self):
        # Initialize and normalize parameter definitions
        params = self.define_parameters()
        # Normalize dict return (name->props) into list of param dicts
        if isinstance(params, dict):
            normalized = []
            for name, props in params.items():
                # Copy props and include name
                prop = dict(props)
                prop['name'] = name
                # Infer type if not provided
                if 'type' not in prop:
                    default = prop.get('default')
                    if isinstance(default, bool):
                        prop['type'] = 'bool'
                    elif isinstance(default, (int,)) and not isinstance(default, bool):
                        prop['type'] = 'int'
                    elif isinstance(default, float):
                        prop['type'] = 'float'
                    else:
                        prop['type'] = 'str'
                normalized.append(prop)
            self.parameters = normalized
        elif isinstance(params, list):
            self.parameters = params
        else:
            raise TypeError(f"define_parameters must return a dict or list, got {type(params)}")

        self._ensure_parameter_steps()

        # Set default variant if not specified
        if self.default_variant is None and self.variants:
            self.default_variant = self.variants[0]
        
        # Current variant tracking
        self.current_variant = self.default_variant

    @abstractmethod
    def define_parameters(self) -> List[Dict[str, Any]]:
        """
        Define the parameters required for the style.
        Must be implemented by subclasses.
        """
        return []

    def define_variant_parameters(self, variant: str) -> List[Dict[str, Any]]:
        """
        Define parameters specific to a variant.
        Override this method to provide variant-specific parameters.
        
        Args:
            variant (str): The variant name
            
        Returns:
            List[Dict[str, Any]]: List of parameter definitions for the variant
        """
        return []

    def get_available_variants(self) -> List[str]:
        """
        Get list of available variants for this style.
        
        Returns:
            List[str]: List of available variant names
        """
        return self.variants.copy()

    def validate_variant(self, variant: str) -> bool:
        """
        Validate if a variant is supported by this style.
        
        Args:
            variant (str): The variant to validate
            
        Returns:
            bool: True if variant is valid, False otherwise
        """
        return variant in self.variants

    def get_variant_parameters(self, variant: str = None) -> List[Dict[str, Any]]:
        """
        Get all parameters for a specific variant including base parameters.
        
        Args:
            variant (str): The variant name (uses current_variant if None)
            
        Returns:
            List[Dict[str, Any]]: Combined list of base and variant-specific parameters
        """
        if variant is None:
            variant = self.current_variant
        
        if not self.validate_variant(variant) and variant is not None:
            raise ValueError(f"Invalid variant '{variant}' for style '{self.name}'")
        
        # Get base parameters
        all_params = self.parameters.copy()
        
        # Add variant-specific parameters
        variant_params = self.define_variant_parameters(variant)
        all_params.extend(variant_params)
        
        return all_params

    def set_variant(self, variant: str) -> bool:
        """
        Set the current variant for this style.
        
        Args:
            variant (str): The variant to set
            
        Returns:
            bool: True if variant was set successfully, False otherwise
        """
        if self.validate_variant(variant):
            self.current_variant = variant
            return True
        return False

    def get_current_variant(self) -> str:
        """
        Get the current variant for this style.
        
        Returns:
            str: Current variant name
        """
        return self.current_variant

    def apply(self, frame: Optional[np.ndarray], params: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """
        Apply the style to the given frame using the provided parameters.

        Args:
            frame (numpy.ndarray): The input video frame.
            params (dict): Parameters for the style.

        Returns:
            numpy.ndarray: The styled video frame.
        """
        if frame is None or not isinstance(frame, np.ndarray):
            raise ValueError("Invalid frame provided. Expected a NumPy array.")

        # Use default parameters if params are not provided
        params = self.validate_params(params or {})

        # Default behavior is to return the original frame (no-op)
        return frame

    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and set default values for parameters.

        Args:
            params (dict): Parameters to validate.

        Returns:
            dict: Validated parameters with defaults applied.
        """
        validated = {}

        # Get all parameters including variant-specific ones
        if hasattr(self, 'current_variant'):
            all_params = self.get_variant_parameters(self.current_variant)
        else:
            all_params = self.get_variant_parameters()

        # Create a mapping of parameter names to their definitions
        param_map = {p['name']: p for p in all_params}
        
        for param in all_params:
            name = param["name"]
            value = params.get(name, param.get("default"))

            # Validate range for numeric parameters
            if param["type"] in ["int", "float"]:
                min_val = param.get("min", float("-inf"))
                max_val = param.get("max", float("inf"))
                if not (min_val <= value <= max_val):
                    # Clamp value to valid range instead of raising error
                    if value < min_val:
                        value = min_val
                    elif value > max_val:
                        value = max_val

            # Validate options for string parameters
            if param["type"] == "str" and "options" in param:
                if value not in param["options"]:
                    # Use default if invalid option provided
                    value = param.get("default", param["options"][0])

            validated[name] = value

        return validated

    def describe(self) -> str:
        """
        Get a description of the style.

        Returns:
            str: Description of the style.
        """
        return f"{self.name} ({self.category})"

    def get_style_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the style.

        Returns:
            Dict[str, Any]: Style information including name, category, variants, and parameters
        """
        return {
            "name": self.name,
            "category": self.category,
            "variants": self.get_available_variants(),
            "current_variant": self.get_current_variant(),
            "parameters": self.get_variant_parameters(self.current_variant),
            "description": self.describe()
        }

    def _ensure_parameter_steps(self) -> None:
        """
        Ensure all numeric parameters expose an explicit step value.
        Emits a warning the first time a parameter is auto-filled.
        """
        for param in self.parameters:
            param_type = param.get('type')
            if param_type not in {'int', 'float'}:
                continue
            if 'step' in param:
                continue

            default_step = 1 if param_type == 'int' else 0.1
            param['step'] = default_step

            key = (self.__class__, param.get('name', '<unnamed>'))
            if key not in _MISSING_STEP_WARNINGS:
                _MISSING_STEP_WARNINGS.add(key)
                _logger.warning(
                    "Style %s parameter '%s' missing explicit 'step'; defaulting to %s. "
                    "Update the parameter metadata to provide a step for consistent UI/config behaviour.",
                    self.__class__.__name__,
                    param.get('name', '<unnamed>'),
                    default_step,
                )
