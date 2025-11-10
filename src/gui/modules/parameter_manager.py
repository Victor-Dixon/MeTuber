"""
Parameter Manager Module for Dreamscape V2 Professional

Handles all parameter-related functionality including embedded widgets,
parameter updates, and fallback parameter creation.
"""

import logging
from PyQt5.QtWidgets import (
    QSlider, QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox, QLabel, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt


class ParameterManager:
    """Manages all parameter-related functionality."""
    
    def __init__(self, main_window):
        """Initialize parameter manager with reference to main window."""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Parameter storage
        self.current_embedded_params = {}
        self.current_filter_name = None
        self.current_style = None
        
        # Throttling for parameter updates
        self.last_parameter_update = 0
        self.parameter_update_threshold = 0.1  # 100ms between updates

    def _get_style_mapping(self):
        """Return mapping of UI-friendly names to concrete styles and preset overrides."""
        return {
            # Cartoon and related effects
            "🎭 Cartoon Effects": {"style": "Cartoon", "params": {"preset": "Detailed"}},
            "🎨 Cartoon Effects": {"style": "Cartoon", "params": {"preset": "Detailed"}},
            "Cartoon Effects": {"style": "Cartoon", "params": {"preset": "Detailed"}},
            "Cartoon (Detailed)": {"style": "Cartoon", "params": {"preset": "Detailed"}},
            "🎨 Advanced Cartoon": {"style": "Cartoon", "params": {"preset": "Advanced"}},
            "Advanced Cartoon": {"style": "Cartoon", "params": {"preset": "Advanced"}},
            "🎨 Advanced Cartoon (Anime)": {"style": "Cartoon", "params": {"preset": "Anime"}},
            "Advanced Cartoon (Anime)": {"style": "Cartoon", "params": {"preset": "Anime"}},
            "🎨 Cartoon Whole Image": {"style": "Cartoon", "params": {"preset": "Whole"}},
            "Cartoon Whole Image": {"style": "Cartoon", "params": {"preset": "Whole"}},
            "Cartoon (Fast)": {"style": "Cartoon", "params": {"preset": "Fast"}},
            "Cartoon (Advanced)": {"style": "Cartoon", "params": {"preset": "Advanced"}},
            "Cartoon (Anime)": {"style": "Cartoon", "params": {"preset": "Anime"}},
            "Cartoon": "Cartoon",
            # Edge Detection effects
            "🔍 Edge Detection": "Edge Detection",
            "🔍 Advanced Edge Detection": "Advanced Edge Detection",
            "🔍 Line Art": "Line Art",
            # Sketch and drawing effects
            "✏️ Sketch Effects": "Pencil Sketch",
            "✏️ Advanced Pencil Sketch": "Light Pencil Sketch (Color)",
            "✏️ Sketch & Color": "Sketch & Color",
            "✏️ Unified Sketch": "Unified Sketch",
            # Artistic effects
            "🎨 Oil Painting": "Oil Painting",
            "💧 Watercolor": "Watercolor",
            "🎯 Stippling": "Stippling",
            # Basic effects
            "⚡ Brightness Only": "Brightness Only",
            "⚡ Contrast Only": "Contrast Only",
            "🎨 Color Balance": "Color Balance",
            "🌅 Sepia Vibrant": "Sepia Vibrant",
            "🎨 Vibrant Color": "Vibrant Color",
            # Adjustments
            "🔧 Blur": "Blur",
            "🔧 Brightness Contrast": "Brightness Contrast",
            "🔧 Emboss": "Emboss",
            "🔧 Gamma Correction": "Gamma Correction",
            "🔧 Hue Saturation": "Hue Saturation",
            "🔧 Posterize": "Posterize",
            "🔧 Sharpen": "Sharpen",
            "🔧 Solarize": "Solarize",
            "🔧 Threshold": "Threshold",
            "🔧 Vibrance": "Vibrance",
            "🔧 Vintage": "Vintage",
            # Color filters
            "🔄 Invert Colors": "Invert Colors",
            "🎨 Invert Filter": "Invert Filter",
            "🌙 Negative": "Negative",
            "🎨 Unified Invert": "Unified Invert",
            # Distortions
            "🌀 Advanced Halftone": "Advanced Halftone",
            "🎪 Glitch": "Glitch",
            "🔲 Halftone": "Halftone",
            "💡 Light Leak": "Light Leak",
            "🎨 Mosaic": "Mosaic",
            # Effects
            "⚫ Black & White": "Black & White",
            "⚡ Blur Motion": "Blur Motion",
            "⚡ Color Quantization": "Color Quantization",
            "⚡ Emboss & Contrast": "Emboss & Contrast",
            "✨ Glowing Edges": "Glowing Edges",
            "⚡ Lines": "Lines",
            "⚡ Negative Vintage": "Negative Vintage",
            "⚡ Original": "Original",
            # Bitwise operations
            "🔧 Bitwise AND": "Bitwise AND",
            "🔧 Bitwise OR": "Bitwise OR",
            "🔧 Bitwise XOR": "Bitwise XOR",
            # Consolidated fallbacks
            "🎨 Color Effects": "Brightness Only",
            "🎨 Sketch Effects": "Pencil Sketch",
        }
        
    def clear_embedded_parameter_widgets(self):
        """Clear existing embedded parameter widgets."""
        try:
            # Clear the existing parameter layout
            if hasattr(self.main_window, 'params_layout'):
                # Remove all widgets from the layout
                while self.main_window.params_layout.rowCount() > 0:
                    self.main_window.params_layout.removeRow(0)
                    
            # Clear stored widget references safely
            if hasattr(self.main_window, 'embedded_param_widgets'):
                for widget_name, widget in list(self.main_window.embedded_param_widgets.items()):
                    if widget:
                        try:
                            # Check if widget still exists before trying to delete
                            if hasattr(widget, 'isVisible') and widget.isVisible():
                                widget.hide()
                            # Don't call deleteLater() - let Qt handle cleanup
                        except Exception as widget_error:
                            self.logger.debug(f"Widget {widget_name} already cleaned up: {widget_error}")
                self.main_window.embedded_param_widgets.clear()
            else:
                self.main_window.embedded_param_widgets = {}
                
        except Exception as e:
            self.logger.error(f"Error clearing embedded widgets: {e}")
            # Continue anyway - this is not critical
            
    def create_embedded_parameter_widgets(self, parameters):
        """Create parameter widgets and embed them into the existing layout."""
        try:
            # Group parameters by category
            grouped_params = {}
            for param in parameters:
                category = param.get('category', 'Basic')
                if category not in grouped_params:
                    grouped_params[category] = []
                grouped_params[category].append(param)
            
            # Create widgets for each group
            for category, params in grouped_params.items():
                # Add category label
                category_label = QLabel(category)
                category_label.setStyleSheet("color: #0096ff; font-weight: bold; font-size: 12px; margin-top: 10px;")
                self.main_window.params_layout.addRow(category_label)
                
                # Create widgets for each parameter in this category
                for param in params:
                    widget = self.create_embedded_parameter_widget(param)
                    if widget:
                        self.main_window.embedded_param_widgets[param['name']] = widget
                        self.main_window.params_layout.addRow(param['label'], widget)
                        
        except Exception as e:
            self.logger.error(f"Error creating embedded parameter widgets: {e}")
            
    def create_embedded_parameter_widget(self, param):
        """Create a single embedded parameter widget."""
        try:
            param_type = param.get('type', 'slider')
            param_name = param['name']
            param_label = param.get('label', param_name)
            default_value = param.get('default', 0)
            
            # Create container widget
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            
            # Create label
            label = QLabel(param_label)
            label.setMinimumWidth(120)
            label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
            
            if param_type == 'slider':
                # Create slider with value display
                slider = QSlider(Qt.Horizontal)
                min_val = param.get('min', 0)
                max_val = param.get('max', 100)
                slider.setRange(min_val, max_val)
                slider.setValue(default_value)
                
                # Style the slider
                slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: 1px solid #404040;
                        height: 8px;
                        background: #1a1a1a;
                        border-radius: 4px;
                    }
                    
                    QSlider::handle:horizontal {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #0096ff, stop:1 #007acc);
                        border: 2px solid #0096ff;
                        width: 16px;
                        margin: -4px 0;
                        border-radius: 8px;
                    }
                    
                    QSlider::handle:horizontal:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #00a6ff, stop:1 #0088dd);
                    }
                    
                    QSlider::sub-page:horizontal {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0096ff, stop:1 #007acc);
                        border-radius: 4px;
                    }
                """)
                
                # Create value label
                value_label = QLabel(str(default_value))
                value_label.setMinimumWidth(50)
                value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                value_label.setStyleSheet("""
                    QLabel {
                        color: #0096ff;
                        font-weight: bold;
                        font-size: 10px;
                        background: #1a1a1a;
                        border: 1px solid #404040;
                        border-radius: 3px;
                        padding: 2px 6px;
                    }
                """)
                
                # Connect slider to update value label and parameter
                def update_value(value):
                    value_label.setText(str(value))
                    self.on_embedded_parameter_changed(param_name, value)
                
                slider.valueChanged.connect(update_value)
                
                layout.addWidget(label)
                layout.addWidget(slider, 1)  # Slider takes most space
                layout.addWidget(value_label)
                
            elif param_type == 'float':
                # Create float slider with spinbox
                slider = QSlider(Qt.Horizontal)
                min_val = int(param.get('min', 0.0) * 100)
                max_val = int(param.get('max', 1.0) * 100)
                step = param.get('step', 0.1)
                slider.setRange(min_val, max_val)
                slider.setValue(int(default_value * 100))
                
                # Style the slider (same as above)
                slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: 1px solid #404040;
                        height: 8px;
                        background: #1a1a1a;
                        border-radius: 4px;
                    }
                    
                    QSlider::handle:horizontal {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #0096ff, stop:1 #007acc);
                        border: 2px solid #0096ff;
                        width: 16px;
                        margin: -4px 0;
                        border-radius: 8px;
                    }
                    
                    QSlider::handle:horizontal:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #00a6ff, stop:1 #0088dd);
                    }
                    
                    QSlider::sub-page:horizontal {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0096ff, stop:1 #007acc);
                        border-radius: 4px;
                    }
                """)
                
                # Create spinbox for precise control
                spinbox = QDoubleSpinBox()
                spinbox.setMinimum(param.get('min', 0.0))
                spinbox.setMaximum(param.get('max', 1.0))
                spinbox.setValue(default_value)
                spinbox.setSingleStep(step)
                spinbox.setDecimals(2)
                spinbox.setFixedWidth(80)
                spinbox.setStyleSheet("""
                    QDoubleSpinBox {
                        color: #ffffff;
                        background: #1a1a1a;
                        border: 1px solid #404040;
                        border-radius: 3px;
                        padding: 2px 6px;
                        font-size: 10px;
                    }
                    
                    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                        background: #2a2a2a;
                        border: 1px solid #404040;
                        border-radius: 2px;
                    }
                    
                    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                        background: #0096ff;
                    }
                """)
                
                # Connect signals
                def update_from_slider(value):
                    float_value = value / 100.0
                    spinbox.setValue(float_value)
                    self.on_embedded_parameter_changed(param_name, float_value)
                
                def update_from_spinbox(value):
                    slider.setValue(int(value * 100))
                    self.on_embedded_parameter_changed(param_name, value)
                
                slider.valueChanged.connect(update_from_slider)
                spinbox.valueChanged.connect(update_from_spinbox)
                
                layout.addWidget(label)
                layout.addWidget(slider, 1)
                layout.addWidget(spinbox)
                
            elif param_type == 'int':
                # Create integer slider with spinbox
                slider = QSlider(Qt.Horizontal)
                min_val = param.get('min', 0)
                max_val = param.get('max', 100)
                step = param.get('step', 1)
                slider.setRange(min_val, max_val)
                slider.setValue(default_value)
                
                # Style the slider (same as above)
                slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: 1px solid #404040;
                        height: 8px;
                        background: #1a1a1a;
                        border-radius: 4px;
                    }
                    
                    QSlider::handle:horizontal {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #0096ff, stop:1 #007acc);
                        border: 2px solid #0096ff;
                        width: 16px;
                        margin: -4px 0;
                        border-radius: 8px;
                    }
                    
                    QSlider::handle:horizontal:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #00a6ff, stop:1 #0088dd);
                    }
                    
                    QSlider::sub-page:horizontal {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0096ff, stop:1 #007acc);
                        border-radius: 4px;
                    }
                """)
                
                # Create spinbox for precise control
                spinbox = QSpinBox()
                spinbox.setMinimum(min_val)
                spinbox.setMaximum(max_val)
                spinbox.setValue(default_value)
                spinbox.setSingleStep(step)
                spinbox.setFixedWidth(80)
                spinbox.setStyleSheet("""
                    QSpinBox {
                        color: #ffffff;
                        background: #1a1a1a;
                        border: 1px solid #404040;
                        border-radius: 3px;
                        padding: 2px 6px;
                        font-size: 10px;
                    }
                    
                    QSpinBox::up-button, QSpinBox::down-button {
                        background: #2a2a2a;
                        border: 1px solid #404040;
                        border-radius: 2px;
                    }
                    
                    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                        background: #0096ff;
                    }
                """)
                
                # Connect signals
                def update_from_slider(value):
                    spinbox.setValue(value)
                    self.on_embedded_parameter_changed(param_name, value)
                
                def update_from_spinbox(value):
                    slider.setValue(value)
                    self.on_embedded_parameter_changed(param_name, value)
                
                slider.valueChanged.connect(update_from_slider)
                spinbox.valueChanged.connect(update_from_spinbox)
                
                layout.addWidget(label)
                layout.addWidget(slider, 1)
                layout.addWidget(spinbox)
                
            elif param_type == 'bool':
                # Create checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(default_value)
                checkbox.setStyleSheet("""
                    QCheckBox {
                        color: #ffffff;
                        font-size: 11px;
                    }
                    
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                        border: 2px solid #404040;
                        border-radius: 3px;
                        background: #1a1a1a;
                    }
                    
                    QCheckBox::indicator:checked {
                        background: #0096ff;
                        border: 2px solid #0096ff;
                    }
                    
                    QCheckBox::indicator:hover {
                        border: 2px solid #0096ff;
                    }
                """)
                
                # Connect signal
                checkbox.toggled.connect(lambda checked: self.on_embedded_parameter_changed(param_name, checked))
                
                layout.addWidget(label)
                layout.addWidget(checkbox)
                layout.addStretch()
                
            elif param_type == 'str':
                # Create combobox for string options
                combobox = QComboBox()
                options = param.get('options', [])
                combobox.addItems(options)
                combobox.setCurrentText(str(default_value))
                combobox.setFixedWidth(120)
                combobox.setStyleSheet("""
                    QComboBox {
                        color: #ffffff;
                        background: #1a1a1a;
                        border: 1px solid #404040;
                        border-radius: 3px;
                        padding: 4px 8px;
                        font-size: 10px;
                    }
                    
                    QComboBox::drop-down {
                        border: none;
                        width: 20px;
                    }
                    
                    QComboBox::down-arrow {
                        image: none;
                        border-left: 6px solid transparent;
                        border-right: 6px solid transparent;
                        border-top: 6px solid #0096ff;
                    }
                    
                    QComboBox QAbstractItemView {
                        background: #2a2a2a;
                        border: 2px solid #404040;
                        selection-background-color: #0096ff;
                        color: white;
                    }
                """)
                
                # Connect signal
                combobox.currentTextChanged.connect(lambda text: self.on_embedded_parameter_changed(param_name, text))
                
                layout.addWidget(label)
                layout.addWidget(combobox)
                layout.addStretch()
            
            return container
            
        except Exception as e:
            self.logger.error(f"Error creating embedded parameter widget: {e}")
            return QWidget()
            
    def on_embedded_parameter_changed(self, param_name, value):
        """Handle parameter changes from embedded widgets with throttling."""
        try:
            import time
            current_time = time.time()
            
            # Throttle parameter updates to prevent lag
            if current_time - self.last_parameter_update < self.parameter_update_threshold:
                return  # Skip this update if too soon
            
            # Update the current parameters
            self.current_embedded_params[param_name] = value
            self.last_parameter_update = current_time
            
            self.logger.info(f"🎛️ PARAMETER CHANGE: {param_name} = {value}")
            self.logger.info(f"🎛️ ALL CURRENT PARAMETERS: {self.current_embedded_params}")
            
            # Apply the effect with updated parameters
            if self.current_filter_name:
                self.apply_embedded_effect(self.current_filter_name, self.current_embedded_params)
            else:
                # Try to get the filter name from the main window
                if hasattr(self.main_window, 'current_style') and self.main_window.current_style:
                    style_name = self.main_window.current_style.name
                    self.apply_embedded_effect(style_name, self.current_embedded_params)
                else:
                    self.logger.warning("No current filter name set")
                    
            # Update activity time in webcam service for adaptive processing
            if hasattr(self.main_window, 'webcam_manager') and self.main_window.webcam_manager:
                if hasattr(self.main_window.webcam_manager, 'webcam_service'):
                    webcam_service = self.main_window.webcam_manager.webcam_service
                    if hasattr(webcam_service, 'last_activity_time'):
                        webcam_service.last_activity_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error handling embedded parameter change: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    def apply_embedded_effect(self, filter_name, parameters):
        """Apply effect using embedded widget parameters."""
        try:
            # Load and apply the style with parameters
            if hasattr(self.main_window, 'style_manager'):
                style_manager = self.main_window.style_manager
            else:
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
                
            style_mapping = self._get_style_mapping()
            mapping_entry = style_mapping.get(filter_name, filter_name)
            if isinstance(mapping_entry, dict):
                actual_style_name = mapping_entry.get("style", filter_name)
                override_params = mapping_entry.get("params", {})
            else:
                actual_style_name = mapping_entry
                override_params = {}
            
            parameters = parameters or {}
            combined_params = {**override_params, **parameters}
            
            # Get the style instance
            style_instance = style_manager.get_style(actual_style_name)
            
            if style_instance:
                self.logger.info(f"🎨 Applying {actual_style_name} with params: {combined_params}")
                
                # Update the webcam service with the style and parameters
                if hasattr(self.main_window, 'webcam_manager') and self.main_window.webcam_manager:
                    # Update through the webcam manager
                    self.main_window.webcam_manager.update_style(actual_style_name, combined_params)
                    self.logger.info(f"🔧 Updated webcam manager with style '{actual_style_name}' and parameters: {combined_params}")
                elif hasattr(self.main_window, 'webcam_service') and self.main_window.webcam_service:
                    # Fallback to direct webcam service
                    self.main_window.webcam_service.update_style(style_instance, combined_params)
                    self.logger.info(f"🔧 Updated webcam service with parameters: {combined_params}")
                else:
                    self.logger.warning("No webcam service or manager available")
                    
            else:
                self.logger.error(f"Style '{actual_style_name}' not found")
                
        except Exception as e:
            self.logger.error(f"Error applying embedded effect: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    def create_fallback_parameters(self, filter_name):
        """Create fallback parameters when style parameters can't be loaded."""
        filter_name_lower = filter_name.lower()
        
        if "edge" in filter_name_lower or "detection" in filter_name_lower:
            return [
                {
                    'name': 'threshold1',
                    'type': 'slider',
                    'min': 0,
                    'max': 255,
                    'default': 100,
                    'label': 'Lower Threshold',
                    'category': 'Edge Detection'
                },
                {
                    'name': 'threshold2',
                    'type': 'slider',
                    'min': 0,
                    'max': 255,
                    'default': 200,
                    'label': 'Upper Threshold',
                    'category': 'Edge Detection'
                },
                {
                    'name': 'blur_kernel',
                    'type': 'slider',
                    'min': 1,
                    'max': 15,
                    'default': 5,
                    'label': 'Blur Kernel Size',
                    'category': 'Preprocessing'
                },
                {
                    'name': 'algorithm',
                    'type': 'str',
                    'options': ['Canny', 'Sobel', 'Laplacian'],
                    'default': 'Canny',
                    'label': 'Algorithm',
                    'category': 'Advanced'
                }
            ]
        elif "cartoon" in filter_name_lower:
            return [
                {
                    'name': 'edge_threshold',
                    'type': 'slider',
                    'min': 0,
                    'max': 255,
                    'default': 50,
                    'label': 'Edge Threshold',
                    'category': 'Basic'
                },
                {
                    'name': 'color_saturation',
                    'type': 'float',
                    'min': 0.1,
                    'max': 3.0,
                    'default': 1.5,
                    'label': 'Color Saturation',
                    'category': 'Basic'
                },
                {
                    'name': 'blur_strength',
                    'type': 'slider',
                    'min': 1,
                    'max': 15,
                    'default': 5,
                    'label': 'Blur Strength',
                    'category': 'Basic'
                },
                {
                    'name': 'mode',
                    'type': 'str',
                    'options': ['Basic', 'Advanced', 'Anime'],
                    'default': 'Basic',
                    'label': 'Cartoon Mode',
                    'category': 'Advanced'
                }
            ]
        elif "sketch" in filter_name_lower:
            return [
                {
                    'name': 'line_thickness',
                    'type': 'slider',
                    'min': 1,
                    'max': 10,
                    'default': 3,
                    'label': 'Line Thickness',
                    'category': 'Basic'
                },
                {
                    'name': 'detail_level',
                    'type': 'slider',
                    'min': 0,
                    'max': 100,
                    'default': 50,
                    'label': 'Detail Level',
                    'category': 'Basic'
                },
                {
                    'name': 'preserve_colors',
                    'type': 'bool',
                    'default': False,
                    'label': 'Preserve Colors',
                    'category': 'Advanced'
                }
            ]
        elif "color" in filter_name_lower:
            return [
                {
                    'name': 'brightness',
                    'type': 'slider',
                    'min': -100,
                    'max': 100,
                    'default': 0,
                    'label': 'Brightness',
                    'category': 'Basic'
                },
                {
                    'name': 'contrast',
                    'type': 'float',
                    'min': 0.5,
                    'max': 3.0,
                    'default': 1.0,
                    'label': 'Contrast',
                    'category': 'Basic'
                },
                {
                    'name': 'saturation',
                    'type': 'float',
                    'min': 0.0,
                    'max': 2.0,
                    'default': 1.0,
                    'label': 'Saturation',
                    'category': 'Basic'
                }
            ]
        else:
            # Generic fallback
            return [
                {
                    'name': 'intensity',
                    'type': 'slider',
                    'min': 0,
                    'max': 100,
                    'default': 50,
                    'label': 'Effect Intensity',
                    'category': 'Basic'
                },
                {
                    'name': 'quality',
                    'type': 'str',
                    'options': ['Low', 'Medium', 'High'],
                    'default': 'Medium',
                    'label': 'Quality',
                    'category': 'Advanced'
                },
                {
                    'name': 'enable_effect',
                    'type': 'bool',
                    'default': True,
                    'label': 'Enable Effect',
                    'category': 'Basic'
                }
            ]
            
    def update_parameter_controls(self, filter_name):
        """Update parameter controls for a specific filter."""
        try:
            self.logger.info(f"Updating parameter controls for: {filter_name}")
            
            # Clear existing widgets
            self.clear_embedded_parameter_widgets()
            
            # Get the actual style instance and its parameters
            style_instance = self.get_style_instance(filter_name)
            if style_instance:
                # Get parameters from the style instance
                if hasattr(style_instance, 'define_parameters'):
                    style_params = style_instance.define_parameters()
                    parameters = self.convert_style_parameters_to_ui_format(style_params)
                elif hasattr(style_instance, 'parameters'):
                    # Handle both list and dict formats
                    style_params = style_instance.parameters
                    if callable(style_params):
                        style_params = style_params()
                    parameters = self.convert_style_parameters_to_ui_format(style_params)
                else:
                    # Fallback to generic parameters
                    parameters = self.create_fallback_parameters(filter_name)
            else:
                # Fallback to generic parameters if style not found
                parameters = self.create_fallback_parameters(filter_name)
            
            self.logger.info(f"Created parameters for {filter_name}: {[p['name'] for p in parameters]}")
            
            # Create embedded widgets
            self.create_embedded_parameter_widgets(parameters)
            
            # Store current filter name
            self.current_filter_name = filter_name
            
            self.logger.info(f"Parameter controls updated for: {filter_name}")
            
        except Exception as e:
            self.logger.error(f"Error updating parameter controls: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def get_style_instance(self, filter_name):
        """Get the style instance for a given filter name."""
        try:
            # Get style manager from main window
            if hasattr(self.main_window, 'style_manager'):
                style_manager = self.main_window.style_manager
            else:
                # Fallback to creating a new style manager
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
            
            style_mapping = self._get_style_mapping()
            mapping_entry = style_mapping.get(filter_name, filter_name)
            if isinstance(mapping_entry, dict):
                actual_style_name = mapping_entry.get("style", filter_name)
            else:
                actual_style_name = mapping_entry
            
            # Try to get the style instance
            style_instance = style_manager.get_style(actual_style_name)
            
            if style_instance:
                self.logger.info(f"✅ Found style: {actual_style_name}")
                return style_instance
            else:
                self.logger.warning(f"❌ Style not found: {actual_style_name}")
                # Try to find a similar style
                available_styles = style_manager.get_available_styles()
                self.logger.info(f"Available styles: {available_styles}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting style instance for {filter_name}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def convert_style_parameters_to_ui_format(self, style_params):
        """Convert style parameters to UI widget format."""
        try:
            ui_parameters = []
            
            # Handle different parameter formats
            if isinstance(style_params, dict):
                # Dictionary format: {"param_name": {"default": 9, "min": 1, "max": 20}}
                for param_name, param_def in style_params.items():
                    ui_param = {
                        'name': param_name,
                        'label': self._create_nice_label(param_name),
                        'category': 'Basic'
                    }
                    
                    if isinstance(param_def, dict):
                        # New format: {"default": 9, "min": 1, "max": 20}
                        ui_param.update({
                            'default': param_def.get('default', 0),
                            'min': param_def.get('min', 0),
                            'max': param_def.get('max', 100),
                            'step': param_def.get('step', 1)
                        })
                        
                        # Determine type based on values
                        if isinstance(param_def.get('default'), float):
                            ui_param['type'] = 'float'
                        elif isinstance(param_def.get('default'), bool):
                            ui_param['type'] = 'bool'
                        else:
                            ui_param['type'] = 'slider'
                    else:
                        # Simple value format
                        ui_param.update({
                            'default': param_def,
                            'min': 0,
                            'max': 100,
                            'step': 1,
                            'type': 'slider'
                        })
                    
                    ui_parameters.append(ui_param)
                    
            elif isinstance(style_params, list):
                # List format: [{"name": "param", "default": 9, "min": 1, "max": 20}]
                for param in style_params:
                    ui_param = {
                        'name': param.get('name', 'unknown'),
                        'label': self._create_nice_label(param.get('label', param.get('name', 'Unknown'))),
                        'type': param.get('type', 'slider'),
                        'default': param.get('default', 0),
                        'min': param.get('min', 0),
                        'max': param.get('max', 100),
                        'step': param.get('step', 1),
                        'category': param.get('category', 'Basic')
                    }
                    
                    # Handle special parameter types
                    if param.get('type') == 'str' and 'options' in param:
                        ui_param['options'] = param.get('options', [])
                        ui_param['type'] = 'str'
                    elif param.get('type') == 'bool':
                        ui_param['type'] = 'bool'
                    elif param.get('type') == 'float':
                        ui_param['type'] = 'float'
                    
                    ui_parameters.append(ui_param)
            
            self.logger.info(f"Converted {len(ui_parameters)} parameters to UI format")
            return ui_parameters
            
        except Exception as e:
            self.logger.error(f"Error converting style parameters: {e}")
            return []
    
    def _create_nice_label(self, param_name):
        """Create a nice, readable label from parameter name."""
        try:
            # Handle common parameter names
            label_mapping = {
                'bilateral_filter_diameter': 'Filter Diameter',
                'bilateral_filter_sigmaColor': 'Color Sigma',
                'bilateral_filter_sigmaSpace': 'Space Sigma',
                'canny_threshold1': 'Threshold 1',
                'canny_threshold2': 'Threshold 2',
                'color_levels': 'Color Levels',
                'threshold1': 'Threshold 1',
                'threshold2': 'Threshold 2',
                'aperture_size': 'Aperture Size',
                'edge_threshold1': 'Edge Threshold 1',
                'edge_threshold2': 'Edge Threshold 2',
                'edge_method': 'Edge Method',
                'edge_thickness': 'Edge Thickness',
                'sharpen_intensity': 'Sharpen Intensity',
                'posterization_levels': 'Posterization Levels',
                'saturation_boost': 'Saturation Boost',
                'brightness_boost': 'Brightness Boost',
                'sketch_blend': 'Sketch Blend',
                'lighten_background': 'Lighten Background',
                'lighten_threshold': 'Lighten Threshold',
                'enable_color_quantization': 'Enable Color Quantization',
                'color_clusters': 'Color Clusters',
                'anime_mode': 'Anime Mode',
                'outline_thickness': 'Outline Thickness',
                'blur_kernel': 'Blur Kernel',
                'algorithm': 'Algorithm',
                'intensity': 'Intensity',
                'smoothing': 'Smoothing',
                'edge_strength': 'Edge Strength',
                'quality': 'Quality',
                'speed': 'Speed',
                'blend': 'Blend',
                'threshold': 'Threshold',
                'brightness': 'Brightness',
                'contrast': 'Contrast',
                'saturation': 'Saturation',
                'hue': 'Hue',
                'gamma': 'Gamma',
                'vibrance': 'Vibrance',
                'vintage': 'Vintage',
                'emboss': 'Emboss',
                'posterize': 'Posterize',
                'sharpen': 'Sharpen',
                'solarize': 'Solarize',
                'invert': 'Invert',
                'negative': 'Negative',
                'glitch': 'Glitch',
                'halftone': 'Halftone',
                'mosaic': 'Mosaic',
                'light_leak': 'Light Leak',
                'glowing_edges': 'Glowing Edges',
                'motion_blur': 'Motion Blur',
                'color_quantization': 'Color Quantization',
                'emboss_contrast': 'Emboss & Contrast',
                'negative_vintage': 'Negative Vintage',
                'original': 'Original',
                'lines': 'Lines',
                'hough_lines': 'Hough Lines',
                'canny_edge': 'Canny Edge',
                'bitwise_and': 'Bitwise AND',
                'bitwise_or': 'Bitwise OR',
                'bitwise_xor': 'Bitwise XOR',
                'oil_painting': 'Oil Painting',
                'watercolor': 'Watercolor',
                'stippling': 'Stippling',
                'line_art': 'Line Art',
                'pencil_sketch': 'Pencil Sketch',
                'sketch_color': 'Sketch & Color',
                'unified_sketch': 'Unified Sketch',
                'advanced_cartoon': 'Cartoon (Advanced)',
                'advanced_cartoon_anime': 'Cartoon (Anime)',
                'cartoon_whole_image': 'Cartoon (Whole)',
                'advanced_edge_detection': 'Advanced Edge Detection',
                'advanced_pencil_sketch': 'Advanced Pencil Sketch',
                'advanced_halftone': 'Advanced Halftone',
                'unified_cartoon': 'Unified Cartoon',
                'unified_invert': 'Unified Invert',
                'brightness_only': 'Brightness Only',
                'contrast_only': 'Contrast Only',
                'color_balance': 'Color Balance',
                'sepia_vibrant': 'Sepia Vibrant',
                'vibrant_color': 'Vibrant Color',
                'brightness_contrast': 'Brightness & Contrast',
                'gamma_correction': 'Gamma Correction',
                'hue_saturation': 'Hue & Saturation',
                'black_white': 'Black & White',
                'blur_motion': 'Motion Blur',
                'emboss_contrast': 'Emboss & Contrast',
                'negative_vintage': 'Negative Vintage',
                'invert_colors': 'Invert Colors',
                'invert_filter': 'Invert Filter',
                'glowing_edges': 'Glowing Edges',
                'lines': 'Lines',
                'original': 'Original',
                'hough_lines': 'Hough Lines',
                'canny_edge': 'Canny Edge',
                'bitwise_and': 'Bitwise AND',
                'bitwise_or': 'Bitwise OR',
                'bitwise_xor': 'Bitwise XOR',
            }
            
            # Check if we have a mapping for this parameter
            if param_name in label_mapping:
                return label_mapping[param_name]
            
            # Otherwise, create a nice label from the parameter name
            # Replace underscores with spaces and capitalize
            label = param_name.replace('_', ' ').title()
            
            # Handle common prefixes
            if label.startswith('Bilateral Filter '):
                label = label.replace('Bilateral Filter ', '')
            elif label.startswith('Edge '):
                label = label.replace('Edge ', '')
            elif label.startswith('Color '):
                label = label.replace('Color ', '')
            elif label.startswith('Light '):
                label = label.replace('Light ', '')
            elif label.startswith('Advanced '):
                label = label.replace('Advanced ', '')
            elif label.startswith('Unified '):
                label = label.replace('Unified ', '')
            
            return label
            
        except Exception as e:
            self.logger.error(f"Error creating nice label for {param_name}: {e}")
            return param_name.replace('_', ' ').title()
            
    def get_widget_type(self, props):
        """Determine widget type from parameter properties."""
        param_type = props.get('type', 'slider')
        
        if param_type == 'float':
            return 'float'
        elif param_type == 'int':
            return 'int'
        elif param_type == 'bool':
            return 'bool'
        elif param_type == 'str' or 'options' in props:
            return 'str'
        else:
            return 'slider'
            
    def hide_old_parameter_controls(self):
        """Hide the old static parameter controls when using draggable widgets."""
        try:
            # Hide the old parameter sliders and labels
            if hasattr(self.main_window, 'param1_slider'):
                self.main_window.param1_slider.hide()
                self.main_window.param1_label.hide()
            if hasattr(self.main_window, 'param2_slider'):
                self.main_window.param2_slider.hide()
                self.main_window.param2_label.hide()
            if hasattr(self.main_window, 'param3_slider'):
                self.main_window.param3_slider.hide()
                self.main_window.param3_label.hide()
            if hasattr(self.main_window, 'param4_slider'):
                self.main_window.param4_slider.hide()
                self.main_window.param4_label.hide()
                
            # Hide the old effect variant combo
            if hasattr(self.main_window, 'effect_variant_combo'):
                self.main_window.effect_variant_combo.hide()
                
            self.logger.info("Hidden old parameter controls - using draggable widgets")
        except Exception as e:
            self.logger.error(f"Error hiding old controls: {e}")
            
    def show_old_parameter_controls(self):
        """Show the old static parameter controls as fallback."""
        try:
            # Show the old parameter sliders and labels
            if hasattr(self.main_window, 'param1_slider'):
                self.main_window.param1_slider.show()
                self.main_window.param1_label.show()
            if hasattr(self.main_window, 'param2_slider'):
                self.main_window.param2_slider.show()
                self.main_window.param2_label.show()
            if hasattr(self.main_window, 'param3_slider'):
                self.main_window.param3_slider.show()
                self.main_window.param3_label.show()
            if hasattr(self.main_window, 'param4_slider'):
                self.main_window.param4_slider.show()
                self.main_window.param4_label.show()
                
            # Show the old effect variant combo
            if hasattr(self.main_window, 'effect_variant_combo'):
                self.main_window.effect_variant_combo.show()
                
            self.logger.info("Showed old parameter controls as fallback")
        except Exception as e:
            self.logger.error(f"Error showing old controls: {e}") 