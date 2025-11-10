"""
Effect Manager Module for Dreamscape V2 Professional

Handles all effect-related functionality including effect application,
style management, and effect history tracking.
"""

import logging
from PyQt5.QtWidgets import QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal


class EffectManager:
    """Manages all effect-related functionality."""
    
    def __init__(self, main_window):
        """Initialize effect manager with reference to main window."""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Effect tracking
        self.effects_history = []
        self.current_effect = None
        
        # Signals
        self.effect_applied = pyqtSignal(str)
        
    def create_effect_buttons(self):
        """Create effect buttons in the effects dock."""
        self.logger.info("Creating effect buttons")
        
        # Popular effects list
        effects = [
            "🔍 Edge Detection",
            "🎭 Cartoon Effects", 
            "✏️ Sketch Effects",
            "🎨 Color Effects",
            "💧 Watercolor",
            "⚡ Glitch Effect",
            "🌟 Glow Effect",
            "🎬 Motion Blur",
            "🌈 Color Grading",
            "📸 Portrait Mode",
            "🎪 Vintage",
            "🌌 Cyberpunk"
        ]
        
        # Create effect buttons
        for effect in effects:
            effect_btn = QPushButton(effect)
            effect_btn.setMinimumHeight(40)
            effect_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #404040, stop:1 #2d2d2d);
                    border: 1px solid #404040;
                    border-radius: 6px;
                    padding: 8px;
                    text-align: left;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #505050, stop:1 #404040);
                    border: 1px solid #0096ff;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d2d2d, stop:1 #404040);
                }
            """)
            
            # Connect button to effect application
            effect_btn.clicked.connect(lambda checked, effect_name=effect: self.apply_effect(effect_name))
            
            # Add to effects layout
            self.main_window.effects_layout.addWidget(effect_btn)
            
        # Add stretch to push buttons to top
        self.main_window.effects_layout.addStretch()
        
    def apply_effect(self, effect_name):
        """Apply the selected effect."""
        try:
            self.logger.info(f"🎭 APPLYING EFFECT: {effect_name}")
            
            # Load and apply the style to the webcam service (this method has proper mapping)
            self.load_and_apply_style(effect_name)
            
            # Update parameter controls using the original effect name (not cleaned)
            self.main_window.parameter_manager.update_parameter_controls(effect_name)
            
            self.update_status(f"Applied effect: {effect_name}")
                
        except Exception as e:
            self.logger.error(f"Error applying effect: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
    def embed_widget_content_into_panel(self, filter_name):
        """Embed draggable widget content into the existing parameter panel."""
        try:
            # Clean the filter name (remove emoji)
            clean_filter_name = filter_name.replace('🔍', '').replace('🎨', '').replace('🌊', '').replace('⚡', '').strip()
            
            # Clear existing parameter widgets
            self.main_window.parameter_manager.clear_embedded_parameter_widgets()
            
            # Get style manager
            if hasattr(self.main_window, 'style_manager'):
                style_manager = self.main_window.style_manager
            else:
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
                
            # Get style instance using clean name
            style_instance = style_manager.get_style(clean_filter_name)
            if not style_instance:
                self.logger.warning(f"No style found for filter: {clean_filter_name}")
                # Use fallback parameters
                parameters = self.main_window.parameter_manager.create_fallback_parameters(clean_filter_name)
            else:
                # Get parameter definitions
                parameters = []
                if hasattr(style_instance, 'define_parameters'):
                    try:
                        style_params = style_instance.define_parameters()
                        
                        # Convert to widget format
                        if isinstance(style_params, dict):
                            for name, props in style_params.items():
                                param = {
                                    'name': name,
                                    'label': props.get('label', name.replace('_', ' ').title()),
                                    'type': self.main_window.parameter_manager.get_widget_type(props),
                                    'default': props.get('default', 0),
                                    'category': 'Parameters'
                                }
                                
                                # Add type-specific properties
                                if 'min' in props:
                                    param['min'] = props['min']
                                if 'max' in props:
                                    param['max'] = props['max']
                                if 'step' in props:
                                    param['step'] = props['step']
                                if 'options' in props:
                                    param['options'] = props['options']
                                    
                                parameters.append(param)
                                
                        elif isinstance(style_params, list):
                            parameters = style_params
                            
                    except Exception as param_error:
                        self.logger.warning(f"Error extracting parameters: {param_error}")
                        
                # Create comprehensive fallback parameters based on filter type
                if not parameters:
                    parameters = self.main_window.parameter_manager.create_fallback_parameters(clean_filter_name)
            
            # Store the current style for parameter updates
            self.main_window.current_style = style_instance
            self.main_window.parameter_manager.current_filter_name = clean_filter_name
            
            # Create and embed parameter widgets into the existing layout
            self.main_window.parameter_manager.create_embedded_parameter_widgets(parameters)
            
            # Apply the effect immediately
            self.main_window.parameter_manager.apply_embedded_effect(filter_name, parameters)
            
        except Exception as e:
            self.logger.error(f"Error embedding widget content: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    def update_variant_combo(self, effect_name):
        """Update the variant combo box based on the selected effect."""
        self.main_window.effect_variant_combo.clear()
        
        if "Cartoon Effects" in effect_name:
            self.main_window.effect_variant_combo.addItems(["Detailed", "Fast", "Advanced", "Anime", "Whole"])
        elif "Sketch Effects" in effect_name:
            self.main_window.effect_variant_combo.addItems(["Pencil", "Advanced Pencil", "Color Sketch", "Line Art", "Stippling"])
        elif "Color Effects" in effect_name:
            self.main_window.effect_variant_combo.addItems(["Brightness", "Contrast", "Color Balance", "Vibrant", "Sepia", "Black & White", "Negative", "Invert"])
        else:
            self.main_window.effect_variant_combo.addItems(["Standard", "Enhanced", "Pro", "Custom"])
            
    def load_and_apply_style(self, style_name):
        """Load a style and apply it to the webcam service."""
        try:
            # Use pre-loaded style manager for instant access
            if hasattr(self.main_window, 'style_manager_ready'):
                style_manager = self.main_window.style_manager_ready
            else:
                # Fallback if pre-load failed
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
            
            if hasattr(self.main_window, 'parameter_manager'):
                style_mapping = self.main_window.parameter_manager._get_style_mapping()
            else:
                style_mapping = {
                    "🎭 Cartoon Effects": {"style": "Cartoon", "params": {"preset": "Detailed"}},
                    "🎨 Cartoon Effects": {"style": "Cartoon", "params": {"preset": "Detailed"}},
                    "Cartoon Effects": {"style": "Cartoon", "params": {"preset": "Detailed"}},
                    "Cartoon (Detailed)": {"style": "Cartoon", "params": {"preset": "Detailed"}},
                    "🎨 Advanced Cartoon": {"style": "Cartoon", "params": {"preset": "Advanced"}},
                    "🎨 Advanced Cartoon (Anime)": {"style": "Cartoon", "params": {"preset": "Anime"}},
                    "🎨 Cartoon Whole Image": {"style": "Cartoon", "params": {"preset": "Whole"}},
                    "Advanced Cartoon": {"style": "Cartoon", "params": {"preset": "Advanced"}},
                    "Advanced Cartoon (Anime)": {"style": "Cartoon", "params": {"preset": "Anime"}},
                    "Cartoon Whole Image": {"style": "Cartoon", "params": {"preset": "Whole"}},
                    "Cartoon (Fast)": {"style": "Cartoon", "params": {"preset": "Fast"}},
                    "Cartoon (Advanced)": {"style": "Cartoon", "params": {"preset": "Advanced"}},
                    "Cartoon (Anime)": {"style": "Cartoon", "params": {"preset": "Anime"}},
                    "Cartoon": "Cartoon",
                }
            
            mapping_entry = style_mapping.get(style_name, style_name)
            if isinstance(mapping_entry, dict):
                actual_style_name = mapping_entry.get("style", style_name)
                override_params = mapping_entry.get("params", {})
            else:
                actual_style_name = mapping_entry
                override_params = {}
            
            # Load the style
            style_instance = style_manager.get_style(actual_style_name)
            if not style_instance:
                self.logger.warning(f"Style not found: {actual_style_name}")
                return
                
            # Apply the style
            self.main_window.current_style = style_instance
            combined_params = {**override_params}
            self.main_window.pending_params = combined_params
            
            # Update webcam service if running
            if hasattr(self.main_window, 'webcam_manager') and self.main_window.webcam_manager:
                # Update through the webcam manager
                self.main_window.webcam_manager.update_style(actual_style_name, combined_params)
                self.logger.info(f"🔧 Updated webcam manager with style: {actual_style_name} params: {combined_params}")
            elif hasattr(self.main_window, 'webcam_service') and self.main_window.webcam_service:
                # Fallback to direct webcam service
                self.main_window.webcam_service.update_style(style_instance, combined_params)
                self.logger.info(f"🔧 Updated webcam service with style: {actual_style_name} params: {combined_params}")
            else:
                self.logger.warning("No webcam service or manager available")
                
            self.logger.info(f"🎨 STYLE APPLIED: {actual_style_name}")
            
        except Exception as e:
            self.logger.error(f"Error loading and applying style: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    def add_to_favorites(self):
        """Add current effect to favorites."""
        if self.current_effect:
            # Implementation for adding to favorites
            self.logger.info(f"Added {self.current_effect} to favorites")
            
    def update_status(self, message):
        """Update the status bar with a message."""
        if hasattr(self.main_window, 'status_label'):
            self.main_window.status_label.setText(message)
        self.logger.info(message) 

    def add_plugin_effect(self, effect):
        """Add a plugin effect to the effect manager."""
        self.logger.info(f"Adding plugin effect: {effect.name}")
        
        # Store the plugin effect
        if not hasattr(self, 'plugin_effects'):
            self.plugin_effects = {}
        
        self.plugin_effects[effect.name] = effect
        
        # Create a button for the plugin effect
        effect_btn = QPushButton(f"🎨 {effect.name}")
        effect_btn.setMinimumHeight(40)
        effect_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #404040, stop:1 #2d2d2d);
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px;
                text-align: left;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #505050, stop:1 #404040);
                border: 1px solid #0096ff;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d2d2d, stop:1 #404040);
            }
        """)
        
        # Connect button to plugin effect application
        effect_btn.clicked.connect(lambda checked, effect_name=effect.name: self.apply_plugin_effect(effect_name))
        
        # Add to effects layout
        if hasattr(self.main_window, 'effects_layout'):
            self.main_window.effects_layout.addWidget(effect_btn)
    
    def apply_plugin_effect(self, effect_name):
        """Apply a plugin effect."""
        try:
            self.logger.info(f"🎭 APPLYING PLUGIN EFFECT: {effect_name}")
            
            if hasattr(self, 'plugin_effects') and effect_name in self.plugin_effects:
                effect = self.plugin_effects[effect_name]
                
                # Set as current effect
                self.current_effect = effect
                
                # Create UI for the plugin effect
                self.create_plugin_effect_ui(effect)
                
                # Update status
                self.update_status(f"Applied plugin effect: {effect_name}")
                
        except Exception as e:
            self.logger.error(f"Error applying plugin effect: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def create_plugin_effect_ui(self, effect):
        """Create UI for a plugin effect."""
        try:
            # Get the UI component for this effect
            if hasattr(self.main_window, 'plugin_manager'):
                plugin_manager = self.main_window.plugin_manager
                effect_id = f"{effect.name}_{effect.version}" if hasattr(effect, 'version') else effect.name
                ui = plugin_manager.get_effect_ui(effect_id)
                
                if ui:
                    # Clear existing parameter controls
                    if hasattr(self.main_window, 'params_layout'):
                        # Clear the layout
                        while self.main_window.params_layout.count():
                            child = self.main_window.params_layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()
                    
                    # Add the plugin UI to the parameters layout
                    if hasattr(self.main_window, 'params_layout'):
                        self.main_window.params_layout.addWidget(ui)
                        
                        # Connect parameter changes to the main window
                        ui.parameter_changed.connect(self.on_plugin_parameter_changed)
                        
                        self.logger.info(f"Created UI for plugin effect: {effect.name}")
                    else:
                        self.logger.warning("No params_layout found in main window")
                else:
                    self.logger.warning(f"No UI found for plugin effect: {effect.name}")
                    
        except Exception as e:
            self.logger.error(f"Error creating plugin effect UI: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def on_plugin_parameter_changed(self, param_name, value):
        """Handle plugin parameter changes."""
        try:
            self.logger.info(f"Plugin parameter changed: {param_name} = {value}")
            
            # Update the current effect's parameters
            if self.current_effect and hasattr(self.current_effect, 'parameters'):
                # Update the parameter in the effect
                if param_name in self.current_effect.parameters:
                    self.current_effect.parameters[param_name]['default'] = value
                    
                    # Store the updated parameters for the preview manager
                    if not hasattr(self, 'current_effect_params'):
                        self.current_effect_params = {}
                    self.current_effect_params[param_name] = value
                
                # Update webcam service with new parameters
                if hasattr(self.main_window, 'webcam_manager') and self.main_window.webcam_manager:
                    # Get all current parameters
                    all_params = {}
                    if hasattr(self, 'current_effect_params'):
                        all_params = self.current_effect_params.copy()
                    
                    # Update through the webcam manager
                    if self.current_effect:
                        effect_name = self.current_effect.name
                        self.main_window.webcam_manager.update_style(effect_name, all_params)
                        self.logger.info(f"🔧 Updated webcam manager with effect '{effect_name}' and parameters: {all_params}")
                elif hasattr(self.main_window, 'webcam_service') and self.main_window.webcam_service:
                    # Get all current parameters
                    all_params = {}
                    if hasattr(self, 'current_effect_params'):
                        all_params = self.current_effect_params.copy()
                    
                    # Fallback to direct webcam service
                    self.main_window.webcam_service.update_parameters(all_params)
                    self.logger.info(f"🔧 Updated webcam service with parameters: {all_params}")
                else:
                    self.logger.warning("No webcam service or manager available")
                
                # Trigger preview update
                if hasattr(self.main_window, 'preview_manager'):
                    self.main_window.preview_manager.update_preview()
                    
        except Exception as e:
            self.logger.error(f"Error handling plugin parameter change: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}") 