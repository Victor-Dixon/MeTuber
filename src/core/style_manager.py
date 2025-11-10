import logging
import importlib
import pkgutil
import inspect
from typing import Dict, Any, List, Optional, Type
from styles.base import Style

class StyleManager:
    """Manages style loading and instantiation with variant support and proper error handling."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.style_instances: Dict[str, Style] = {}
        self.style_categories: Dict[str, List[str]] = {}
        self.style_variants: Dict[str, List[str]] = {}  # Track variants for each style
        self._load_styles()
    
    def _load_styles(self) -> None:
        """Load all available styles from the styles package."""
        try:
            # List of all style-related packages to scan
            packages_to_scan = ['styles']
            seen_classes = set()
            
            for pkg_name in packages_to_scan:
                self.logger.debug(f"Scanning package: {pkg_name}")
                try:
                    package = importlib.import_module(pkg_name)
                except ImportError as e:
                    self.logger.error(f"Error loading package {pkg_name}: {e}")
                    continue
                
                for _, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                    if ispkg:
                        continue
                    
                    self.logger.debug(f"Found module: {modname}")
                    try:
                        module = importlib.import_module(modname)
                        
                        for cls_name in dir(module):
                            cls = getattr(module, cls_name)
                            if (
                                inspect.isclass(cls) and
                                issubclass(cls, Style) and
                                cls is not Style and
                                not inspect.isabstract(cls) and
                                cls not in seen_classes
                            ):
                                if getattr(cls, "__skip_registration__", False):
                                    self.logger.debug(
                                        "Skipping legacy style class %s.%s during load",
                                        cls.__module__, cls.__name__
                                    )
                                    continue
                                try:
                                    instance = cls()  # Instantiate
                                    seen_classes.add(cls)
                                    
                                    category = getattr(instance, "category", "Uncategorized")
                                    if category not in self.style_categories:
                                        self.style_categories[category] = []
                                    
                                    # Avoid duplicate style names in the same category
                                    if instance.name not in self.style_categories[category]:
                                        self.style_categories[category].append(instance.name)
                                    
                                    self.style_instances[instance.name] = instance
                                    
                                    # Track variants for this style
                                    if hasattr(instance, 'variants') and instance.variants:
                                        self.style_variants[instance.name] = instance.variants.copy()
                                        self.logger.info(f"Loaded style: {instance.name} (Category: {category}, Variants: {instance.variants})")
                                    else:
                                        self.logger.info(f"Loaded style: {instance.name} (Category: {category})")
                                    
                                except Exception as instantiation_error:
                                    self.logger.error(f"Failed to instantiate style '{cls.__name__}': {instantiation_error}")
                    
                    except Exception as module_error:
                        self.logger.error(f"Failed to load module '{modname}': {module_error}")
            
        except Exception as e:
            self.logger.error(f"Error loading styles: {e}")
    
    def get_style(self, name: str) -> Optional[Style]:
        """Get a style instance by name."""
        try:
            return self.style_instances.get(name)
        except Exception as e:
            self.logger.error(f"Error getting style {name}: {e}")
            return None
    
    def get_style_with_variant(self, name: str, variant: str = None) -> Optional[Style]:
        """Get a style instance with specific variant set."""
        style = self.get_style(name)
        if style and hasattr(style, 'variants'):
            if variant is None:
                variant = style.default_variant
            if variant in style.variants:
                # Set the variant and return style with updated parameters
                style.set_variant(variant)
                return style
        return style
    
    def get_style_parameters(self, name: str, variant: str = None) -> List[Dict[str, Any]]:
        """Get all parameters for a style including variant-specific ones."""
        style = self.get_style_with_variant(name, variant)
        if not style:
            return []
        
        # Get all parameters including variant-specific ones
        return style.get_variant_parameters(variant)
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get all style categories and their styles."""
        return self.style_categories.copy()
    
    def get_styles_in_category(self, category: str) -> List[str]:
        """Get all styles in a specific category."""
        try:
            return self.style_categories.get(category, []).copy()
        except Exception as e:
            self.logger.error(f"Error getting styles for category {category}: {e}")
            return []
    
    def get_style_variants(self, style_name: str) -> List[str]:
        """Get available variants for a specific style."""
        try:
            return self.style_variants.get(style_name, []).copy()
        except Exception as e:
            self.logger.error(f"Error getting variants for style {style_name}: {e}")
            return []
    
    def get_styles_with_variants(self) -> Dict[str, List[str]]:
        """Get all styles that support variants."""
        return {name: variants for name, variants in self.style_variants.items() if variants}
    
    def validate_style_parameters(self, style_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters for a specific style."""
        try:
            style = self.get_style(style_name)
            if not style:
                self.logger.warning(f"Style {style_name} not found")
                return {}
            
            return style.validate_params(parameters)
        except Exception as e:
            self.logger.error(f"Error validating parameters for style {style_name}: {e}")
            return {}
    
    def get_default_parameters(self, style_name: str, variant: str = None) -> Dict[str, Any]:
        """Get default parameters for a specific style and variant."""
        try:
            style = self.get_style_with_variant(style_name, variant)
            if not style:
                self.logger.warning(f"Style {style_name} not found")
                return {}
            
            # Get all parameters and extract defaults
            params = style.get_variant_parameters(variant)
            defaults = {}
            for param in params:
                if 'default' in param:
                    defaults[param['name']] = param['default']
            
            return defaults
        except Exception as e:
            self.logger.error(f"Error getting default parameters for style {style_name}: {e}")
            return {}
    
    def refresh_styles(self) -> None:
        """Refresh the style list by reloading all styles."""
        self.style_instances.clear()
        self.style_categories.clear()
        self.style_variants.clear()
        self._load_styles()
    
    def get_style_info(self, style_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a style."""
        try:
            style = self.get_style(style_name)
            if not style:
                return None
            
            return style.get_style_info()
        except Exception as e:
            self.logger.error(f"Error getting style info for {style_name}: {e}")
            return None
    
    def get_consolidated_style_mapping(self) -> Dict[str, Dict[str, str]]:
        """Get mapping of old style names to new consolidated styles and variants."""
        return {
            # Cartoon styles mapping
            "cartoon": {"style": "Cartoon", "variant": "Detailed"},
            "advanced_cartoon": {"style": "Cartoon", "variant": "Advanced"},
            "advanced_cartoon2": {"style": "Cartoon", "variant": "Anime"},
            "catoonwholeimage": {"style": "Cartoon", "variant": "Whole"},
            
            # Sketch styles mapping
            "pencil_sketch": {"style": "Sketch", "variant": "Pencil"},
            "advanced_pencil_sketch": {"style": "Sketch", "variant": "Advanced"},
            "sketch_and_color": {"style": "Sketch", "variant": "Color"},
            
            # Invert styles mapping
            "invert_colors": {"style": "Invert", "variant": "Colors"},
            "invert_filter": {"style": "Invert", "variant": "Filter"},
            "negative": {"style": "Invert", "variant": "Negative"},
        }
    
    def migrate_old_style_name(self, old_name: str) -> Optional[Dict[str, str]]:
        """Migrate old style name to new consolidated style and variant."""
        mapping = self.get_consolidated_style_mapping()
        return mapping.get(old_name.lower())
    
    def get_style_complexity(self, style_name: str, variant: str = None) -> str:
        """Get the complexity level of a style for performance optimization."""
        try:
            style = self.get_style_with_variant(style_name, variant)
            if not style:
                return "low"
            
            # Get all parameters for the style
            params = style.get_variant_parameters(variant)
            param_count = len(params)
            
            # Check for computationally expensive operations in the style class
            style_code = inspect.getsource(style.__class__)
            expensive_ops = ['cv2.GaussianBlur', 'cv2.medianBlur', 'cv2.bilateralFilter', 
                           'cv2.Canny', 'cv2.Laplacian', 'cv2.Sobel']
            
            complexity_score = param_count
            for op in expensive_ops:
                if op in style_code:
                    complexity_score += 2
            
            # Determine complexity level
            if complexity_score > 8:
                return "high"
            elif complexity_score > 4:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            self.logger.error(f"Error determining complexity for style {style_name}: {e}")
            return "low"
    
    # Alias methods for compatibility with GUI modules
    def get_style_by_name(self, name: str) -> Optional[Style]:
        """Alias for get_style() method for compatibility."""
        return self.get_style(name)
    
    def load_all_styles(self) -> None:
        """Alias for _load_styles() method for compatibility."""
        self._load_styles()
    
    def pre_load_styles_lazy(self) -> None:
        """Pre-load styles using lazy loading for faster startup."""
        try:
            self.logger.info("Starting lazy style loading...")
            
            # Only load essential styles first (Original, basic effects)
            essential_styles = ['Original', 'BrightnessOnly', 'ContrastOnly']
            
            for style_name in essential_styles:
                try:
                    # Try to load just the essential style
                    self._load_single_style(style_name)
                except Exception as e:
                    self.logger.warning(f"Could not load essential style {style_name}: {e}")
            
            self.logger.info("Essential styles loaded, remaining styles will load on demand")
            
        except Exception as e:
            self.logger.error(f"Error in lazy style loading: {e}")
    
    def _load_single_style(self, style_name: str) -> None:
        """Load a single style by name."""
        try:
            # Import the specific style module
            style_module = importlib.import_module(f"styles.{style_name.lower()}")
            
            # Find the style class
            for cls_name in dir(style_module):
                cls = getattr(style_module, cls_name)
                if (inspect.isclass(cls) and 
                    issubclass(cls, Style) and 
                    cls is not Style and 
                    not inspect.isabstract(cls)):
                    
                    if getattr(cls, "__skip_registration__", False):
                        self.logger.debug(
                            "Skipping legacy style class %s.%s during single load",
                            cls.__module__, cls.__name__
                        )
                        continue

                    instance = cls()
                    category = getattr(instance, "category", "Uncategorized")
                    
                    if category not in self.style_categories:
                        self.style_categories[category] = []
                    
                    if instance.name not in self.style_categories[category]:
                        self.style_categories[category].append(instance.name)
                    
                    self.style_instances[instance.name] = instance
                    
                    if hasattr(instance, 'variants') and instance.variants:
                        self.style_variants[instance.name] = instance.variants.copy()
                    
                    self.logger.info(f"Loaded essential style: {instance.name}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error loading single style {style_name}: {e}")
    
    def pre_load_styles(self) -> None:
        """Pre-load all styles (full loading for compatibility)."""
        self._load_styles() 

    def get_available_styles(self):
        """Get list of all available style names."""
        try:
            return list(self.style_instances.keys())
        except Exception as e:
            self.logger.error(f"Error getting available styles: {e}")
            return [] 