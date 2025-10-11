# webcam_filter_pyqt5.py

import inspect
import sys
import os
import json
import subprocess
import av
import cv2
import numpy as np
import pyvirtualcam
import logging
from logging.handlers import RotatingFileHandler
import pkgutil
import importlib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFormLayout, QSlider, QPushButton, QMessageBox, QFileDialog, QComboBox, QTabWidget, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap
import traceback

# Import GUI components
from gui_components.device_selector import DeviceSelector
from gui_components.style_tab_manager import StyleTabManager
from gui_components.parameter_controls import ParameterControls
from gui_components.action_buttons import ActionButtons

# Import the Style base class and one fallback style
from styles.base import Style
from styles.effects.original import Original

# Import the updated classes
# Make sure these files actually exist in your styles/artistic/ folder!
from styles.artistic.advanced_cartoon import AdvancedCartoon      # Updated import
from styles.artistic.advanced_cartoon2 import AdvancedCartoonAnime # Updated import

# Import the updated WebcamThread
from webcam_threading import WebcamThread  # Ensure this path is correct

# =============================================================================
# 1. Config Load/Save
# =============================================================================

CONFIG_FILE = "config.json"

def load_settings():
    """Load settings from a JSON file if it exists; otherwise use defaults."""
    default_settings = {
        "input_device": "video=C270 HD WEBCAM",  # Example default
        "style": "Original",
        "parameters": {},
        "snapshot_dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snapshots'), # Add default snapshot directory
        "vcam_backend": "obs"  # 'obs' for Zoom/Meet, 'unitycapture' for ingesting into OBS as a source
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                default_settings.update(loaded)
        except (json.JSONDecodeError, IOError):
            logging.warning("Failed to load config.json. Using default settings.")
    return default_settings

def save_settings(settings):
    """Save current settings to a JSON file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        logging.error(f"Error saving settings: {e}")

# =============================================================================
# 2. Device Enumeration (Windows-Only)
# =============================================================================

def convert_device_name_for_pyav(device_name):
    """
    Convert device name from GUI format to PyAV-compatible format.
    Handles both 'video=Device Name' and 'Device Name' formats.
    """
    if not device_name:
        return None
    
    # Remove 'video=' prefix if present
    if device_name.startswith('video='):
        device_name = device_name[6:]
    
    # For Windows DirectShow, we need to use the format that PyAV expects
    # PyAV on Windows with DirectShow expects: 'video=Device Name'
    return f"video={device_name}"

def check_obs_virtual_camera():
    """
    Check if OBS Virtual Camera is available and properly configured.
    """
    try:
        import pyvirtualcam
        # Try to create a test camera to see if OBS backend is available
        test_cam = pyvirtualcam.Camera(640, 480, 30, backend='obs')
        test_cam.close()
        return True, "OBS Virtual Camera is available"
    except Exception as e:
        return False, f"OBS Virtual Camera not available: {e}"

def list_devices():
    """
    List DirectShow devices on Windows using FFmpeg.
    Returns a list of fully qualified device names, e.g. ["video=C270 HD WEBCAM", ...].
    """
    devices = []
    cmd = ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("[dshow") and '"' in line:
                start_idx = line.find('"')
                end_idx = line.rfind('"')
                if start_idx != -1 and end_idx != -1:
                    device_name = line[start_idx + 1:end_idx]
                    # 🚫 Do not offer virtual outputs as capture INPUTS
                    if "Virtual Camera" in device_name:
                        continue
                    devices.append(f"video={device_name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Could not enumerate devices using FFmpeg: {e}")
    return devices

# =============================================================================
# 3. Dynamic Style Loading
# =============================================================================

def load_styles():
    """
    Dynamically loads all Style subclasses from the styles package and categorizes them.

    Returns:
        tuple: 
            - A dictionary of style instances keyed by their names.
            - A dictionary of categories with lists of style names.
    """
    style_instances = {}
    style_categories = {}

    # List of all style-related packages to scan
    packages_to_scan = ['styles']

    seen_classes = set()

    for pkg_name in packages_to_scan:
        logging.debug(f"Scanning package: {pkg_name}")
        try:
            package = importlib.import_module(pkg_name)
        except ImportError as e:
            logging.error(f"Error loading package {pkg_name}: {e}")
            continue

        for _, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            if ispkg:
                continue

            logging.debug(f"Found module: {modname}")
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
                        try:
                            instance = cls()  # Instantiate
                            seen_classes.add(cls)

                            category = getattr(instance, "category", "Uncategorized")
                            if category not in style_categories:
                                style_categories[category] = []

                            # Avoid duplicate style names in the same category
                            if instance.name not in style_categories[category]:
                                style_categories[category].append(instance.name)

                            style_instances[instance.name] = instance
                            logging.info(f"Loaded style: {instance.name} (Category: {category})")

                        except Exception as instantiation_error:
                            logging.error(f"Failed to instantiate style '{cls.__name__}': {instantiation_error}")

            except Exception as module_error:
                logging.error(f"Failed to load module '{modname}': {module_error}")

    return style_instances, style_categories

# =============================================================================
# 4. PyQt5 GUI
# =============================================================================

# Debug mode flag (can be set via config or env)
DEBUG_MODE = os.environ.get("METUBER_DEBUG", "0") == "1"

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snapshots')
if not os.path.exists(SNAPSHOT_DIR):
    os.makedirs(SNAPSHOT_DIR)


def show_error_dialog(parent, message, exc=None):
    """Show a critical error dialog and log the error. If exc is provided, log with traceback."""
    if exc:
        logging.error(message, exc_info=True)
        if DEBUG_MODE:
            message += f"\n\nTraceback:\n{traceback.format_exc()}"
    else:
        logging.error(message)
    QMessageBox.critical(parent, "Error", message)


class WebcamApp(QWidget):
    """
    Main GUI application that manages device selection, style parameters,
    and the start/stop logic for the webcam processing thread.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Webcam Style Selector — Filtered Preview")
        # Optional: uncomment to keep visible for OBS Window Capture
        # self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Thread & style management
        self.thread = None
        self.style_instances, self.style_categories = load_styles()
        self.current_style = None
        self.current_style_params = {}

        # Config settings
        self.settings = load_settings()
        self.snapshot_dir = self.settings.get('snapshot_dir', SNAPSHOT_DIR)

        # Validate and load settings to ensure no invalid parameters
        self.validate_and_load_settings()

        # Initialize the UI
        self.init_ui()

    def validate_and_load_settings(self):
        """Validate and load settings, resetting invalid parameters as needed."""
        for style_name, style_instance in self.style_instances.items():
            style_params = self.settings.get("parameters", {}).get(style_name, {})
            try:
                # Guard against missing validate_params method
                if hasattr(style_instance, 'validate_params'):
                    validated_params = style_instance.validate_params(style_params)
                else:
                    # Fallback: build defaults from parameters
                    validated_params = {
                        param['name']: style_params.get(param['name'], param.get("default", 0))
                        for param in style_instance.parameters
                    }
            except AttributeError as e:
                # Handle styles missing expected attributes (like current_variant)
                logging.warning(f"Invalid parameters for style '{style_name}': {e}. Resetting to defaults.")
                validated_params = {
                    param['name']: param.get("default", 0)
                    for param in style_instance.parameters
                }
            except Exception as e:
                logging.warning(f"Invalid parameters for style '{style_name}': {e}. Resetting to defaults.")
                # Reset to defaults using normalized parameters
                validated_params = {
                    param['name']: param.get("default", 0)
                    for param in style_instance.parameters
                }
            # For 'file' type parameters, if the path no longer exists, reset to default
            for param in style_instance.parameters:
                if param.get("type") == "file":
                    file_path = validated_params.get(param["name"], "")
                    if file_path and not os.path.exists(file_path):
                        # Silently reset missing files (common for texture paths)
                        logging.info(
                            f"File for parameter '{param['name']}' not found at '{file_path}'. Using empty path (texture disabled)."
                        )
                        validated_params[param['name']] = ""  # Empty path = disabled feature
            self.settings["parameters"][style_name] = validated_params
        save_settings(self.settings)
        # If the UI is initialized, update controls to reflect any changed defaults (e.g. file paths)
        if hasattr(self, 'parameter_controls'):
            self.update_parameter_controls()

    def init_ui(self):
        # Main layout with fixed preview at top
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 0) LIVE PREVIEW (fixed size, always visible)
        self.preview_label = QLabel("Preview")
        self.preview_label.setObjectName("Filtered Preview")  # stable name for OBS picker
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background:#111; color:#aaa; padding:8px;")
        self.preview_label.setFixedHeight(200)  # Fixed height for preview
        self.preview_label.setScaledContents(True)  # Scale content to fit
        main_layout.addWidget(self.preview_label)

        # Create scroll area for the rest of the controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create widget to hold scrollable content
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # 1) Device Selector
        devices = list_devices() or ["Enter device manually..."]
        default_device = self.settings.get("input_device", devices[0] if devices else "")
        device_selector = DeviceSelector(self, devices, default_device)
        layout.addLayout(device_selector.create())
        self.device_combo = device_selector.device_combo

        # 1.5) Output / Virtual Camera Settings
        out_group = QGroupBox("Output")
        out_form = QFormLayout()
        self.vcam_backend_combo = QComboBox()
        # Human labels → backend ids
        self.vcam_backend_combo.addItem("OBS Virtual Camera (for Zoom/Meet/Teams)", userData="obs")
        self.vcam_backend_combo.addItem("UnityCapture (add as 'Video Capture Device' in OBS)", userData="unitycapture")
        # Restore from settings
        backend_default = self.settings.get("vcam_backend", "obs")
        idx = max(0, self.vcam_backend_combo.findData(backend_default))
        self.vcam_backend_combo.setCurrentIndex(idx)
        out_form.addRow("Virtual Cam Backend:", self.vcam_backend_combo)
        out_group.setLayout(out_form)
        layout.addWidget(out_group)

        # 2) Style Selector with Categories
        style_tab_manager = StyleTabManager(self, self.style_categories, self.style_instances, self.settings)
        layout.addWidget(style_tab_manager)
        self.style_tab_manager = style_tab_manager

        # Connect style change to parameter update
        style_tab_manager.style_changed.connect(self.update_parameter_controls)

        # 3) Parameter Controls
        self.parameter_controls = ParameterControls(self)
        layout.addWidget(self.parameter_controls)

        # Initialize parameters for whichever style is currently selected
        self.update_parameter_controls()

        # 4) Action Buttons
        action_buttons = ActionButtons(self)
        layout.addLayout(
            action_buttons.create(
                start_callback=self.start_virtual_camera,
                stop_callback=self.stop_virtual_camera,
                snapshot_callback=self.take_snapshot
            )
        )
        self.action_buttons = action_buttons

        # 4.0) Output mode — Virtual Camera toggle (for Zoom/Meet; OBS should Window-Capture preview)
        self.vcam_toggle = QCheckBox("Send frames to Virtual Camera (OBS backend)")
        self.vcam_toggle.setChecked(True)
        layout.addWidget(self.vcam_toggle)

        # 4.1) Auto Optimize Parameters Button
        self.optimize_button = QPushButton("Auto Optimize Parameters")
        self.optimize_button.clicked.connect(self.auto_optimize_parameters)
        layout.addWidget(self.optimize_button)
        # 4.2) Set Snapshot Directory Button
        self.set_snapshot_dir_button = QPushButton("Set Snapshot Save Folder")
        self.set_snapshot_dir_button.clicked.connect(self.set_snapshot_directory)
        layout.addWidget(self.set_snapshot_dir_button)

        # 4.3) Performance Controls
        performance_group = QGroupBox("Performance Settings")
        performance_layout = QFormLayout()
        
        # Max FPS slider
        self.max_fps_slider = QSlider(Qt.Horizontal)
        self.max_fps_slider.setRange(1, 60)
        self.max_fps_slider.setValue(30)
        self.max_fps_label = QLabel("30")
        self.max_fps_slider.valueChanged.connect(lambda v: self.max_fps_label.setText(str(v)))
        performance_layout.addRow("Max FPS:", self.max_fps_slider)
        performance_layout.addRow("", self.max_fps_label)
        
        # Frame skip slider
        self.frame_skip_slider = QSlider(Qt.Horizontal)
        self.frame_skip_slider.setRange(0, 10)
        self.frame_skip_slider.setValue(0)
        self.frame_skip_label = QLabel("0")
        self.frame_skip_slider.valueChanged.connect(lambda v: self.frame_skip_label.setText(str(v)))
        performance_layout.addRow("Frame Skip:", self.frame_skip_slider)
        performance_layout.addRow("", self.frame_skip_label)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)

        # 5) Status Display
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Set up scroll area
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Set main layout and window constraints
        self.setLayout(main_layout)
        self.setMinimumSize(600, 500)  # Minimum window size
        self.setMaximumSize(1200, 800)  # Maximum window size
        self.resize(800, 600)  # Initial window size

    def _show_bgr_on_preview(self, bgr):
        """Render numpy BGR frame to the preview label."""
        try:
            h, w, c = bgr.shape
            rgb = bgr[:, :, ::-1].copy()
            qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
            self.preview_label.setPixmap(QPixmap.fromImage(qimg).scaled(
                self.preview_label.width(), self.preview_label.height(),
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            logging.exception("Preview update failed: %s", e)

    def update_parameter_controls(self):
        """Update parameter controls based on the selected style."""
        selected_style_name = self.style_tab_manager.get_current_style()
        self.current_style = self.style_instances.get(selected_style_name, Original())

        saved_params = self.settings.get("parameters", {})
        self.current_style_params = saved_params.get(selected_style_name, {}).copy()

        if self.current_style:
            logging.info(f"Updating parameters for style: {selected_style_name}")

            # Ensure all parameters have default values if missing
            for param in self.current_style.parameters:
                if param["name"] not in self.current_style_params:
                    self.current_style_params[param["name"]] = param.get("default", 0)
            # For 'file' parameters, if the path no longer exists (e.g. file moved), reset to default to update GUI
            for param in self.current_style.parameters:
                if param.get("type") == "file":
                    current_path = self.current_style_params.get(param["name"], "")
                    if current_path and not os.path.exists(current_path):
                        logging.info(
                            f"File for parameter '{param['name']}' not found at '{current_path}', resetting to default '{param.get('default','')}'"
                        )
                        # Reset internal state and update settings
                        new_default = param.get('default', '')
                        self.current_style_params[param['name']] = new_default
                        # Persist change
                        style_name = self.style_tab_manager.get_current_style()
                        self.settings['parameters'][style_name][param['name']] = new_default
                        save_settings(self.settings)

            # Update controls based on normalized parameters list
            self.parameter_controls.update_parameters(
                self.current_style.parameters,
                self.current_style_params,
                self.on_param_changed
            )
        else:
            logging.warning(f"No style found for: {selected_style_name}")

    def on_param_changed(self, param_name, value, widget):
        """
        Handles parameter changes from the UI controls.

        Args:
            param_name (str): The name of the parameter.
            value (int, float, str, bool): The new value of the parameter.
            widget (QWidget): The widget that triggered the change.
        """
        self.current_style_params[param_name] = value
        selected_style_name = self.style_tab_manager.get_current_style()
        if "parameters" not in self.settings:
            self.settings["parameters"] = {}
        self.settings["parameters"][selected_style_name] = self.current_style_params
        save_settings(self.settings)

        # Update label text for sliders/combos/checkboxes
        if isinstance(widget, QLabel):
            try:
                if isinstance(value, int):
                    widget.setText(f"{value}")
                elif isinstance(value, float):
                    widget.setText(f"{value:.1f}")
                else:
                    widget.setText(str(value))
            except Exception as e:
                logging.error(f"Failed to update label for '{param_name}': {e}")
        elif isinstance(widget, QComboBox):
            logging.debug(f"ComboBox '{param_name}' changed to '{value}'")
        elif isinstance(widget, QCheckBox):
            logging.debug(f"Checkbox '{param_name}' changed to '{value}'")
        else:
            logging.debug(f"Parameter '{param_name}' updated to {value} (widget={type(widget)})")

        # If the webcam thread is running, update parameters on the fly
        if self.thread and self.thread.isRunning():
            thread_params = dict(self.current_style_params)
            thread_params['max_fps'] = self.max_fps_slider.value()
            thread_params['frame_skip'] = self.frame_skip_slider.value()
            self.thread.update_params(thread_params)

    def start_virtual_camera(self):
        """Starts the WebcamThread to capture frames via PyAV and stream them."""
        input_device = self.device_combo.currentText().strip()
        selected_style = self.style_tab_manager.get_current_style()

        if not input_device:
            QMessageBox.warning(self, "Input Device Error", "Please specify a valid input device.")
            return

        # Convert device name to PyAV-compatible format
        pyav_device = convert_device_name_for_pyav(input_device)
        if not pyav_device:
            QMessageBox.warning(self, "Input Device Error", "Invalid device name format.")
            return
        
        # If OUTPUT to VirtualCam is requested, validate OBS backend
        if self.vcam_toggle.isChecked():
            obs_available, obs_message = check_obs_virtual_camera()
            if not obs_available:
                QMessageBox.warning(
                    self, "Virtual Camera Error",
                    f"{obs_message}\n\nPlease ensure:\n"
                    "1) OBS Studio is installed with Virtual Camera\n"
                    "2) 'Start Virtual Camera' is enabled in OBS (or obs-virtualcam driver present)"
                )
                return
            logging.info(f"OBS Virtual Camera check: {obs_message}")

        if not selected_style:
            QMessageBox.warning(self, "Style Selection Error", "Please select a style.")
            return

        # Save current settings
        self.settings["input_device"] = input_device
        self.settings["style"] = selected_style
        self.settings["vcam_backend"] = self.vcam_backend_combo.currentData()
        if "parameters" not in self.settings:
            self.settings["parameters"] = {}
        self.settings["parameters"][selected_style] = self.current_style_params
        save_settings(self.settings)

        # Add performance parameters to style params
        thread_params = dict(self.current_style_params)
        thread_params['max_fps'] = self.max_fps_slider.value()
        thread_params['frame_skip'] = self.frame_skip_slider.value()
        chosen_backend = self.vcam_backend_combo.currentData()
        
        # Initialize and start the thread with converted device name
        self.thread = WebcamThread(
            input_device=pyav_device,
            style_instance=self.style_instances[selected_style],
            style_params=thread_params,
            out_backend=chosen_backend,
            enable_output=self.vcam_toggle.isChecked(),   # ✅ control virtual-cam output
            # Optional explicit input_options override (keeps defaults if omitted)
            # input_options={"framerate": str(thread_params.get("max_fps", 30)), "video_size": "1280x720", "rtbufsize": "100M"},
        )
        self.thread.error_signal.connect(self.display_error)
        self.thread.info_signal.connect(self.display_info)
        self.thread.frame_signal.connect(self._show_bgr_on_preview)  # ✅ live preview
        self.thread.start()

        # Update button states
        self.action_buttons.start_button.setEnabled(False)
        self.action_buttons.stop_button.setEnabled(True)
        self.action_buttons.snapshot_button.setEnabled(True)
        self.status_label.setText("Status: Running")
        logging.info("Virtual camera started.")

    def stop_virtual_camera(self):
        """Stops the webcam thread."""
        if self.thread:
            self.thread.stop()
            self.thread = None
            self.status_label.setText("Status: Stopped")
            logging.info("Virtual camera stopped.")

        # Update button states
        self.action_buttons.start_button.setEnabled(True)
        self.action_buttons.stop_button.setEnabled(False)
        self.action_buttons.snapshot_button.setEnabled(False)

    def set_snapshot_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Snapshot Save Folder", self.snapshot_dir)
        if dir_path:
            self.snapshot_dir = dir_path
            self.settings['snapshot_dir'] = dir_path
            save_settings(self.settings)

    def take_snapshot(self):
        """Capture the last processed frame and let the user save it."""
        if not self.thread or self.thread.last_frame is None:
            QMessageBox.information(self, "Snapshot", "No frame available to save.")
            return
        default_path = os.path.join(self.snapshot_dir, "snapshot.png")
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Snapshot", default_path, "Image Files (*.png *.jpg *.bmp)")
        if save_path:
            cv2.imwrite(save_path, self.thread.last_frame)
            QMessageBox.information(self, "Snapshot", f"Snapshot saved to:\n{save_path}")
            logging.info(f"Snapshot saved to: {save_path}")

    def display_error(self, message, exc=None):
        """Show error messages via a dialog and stop the thread."""
        show_error_dialog(self, message, exc)
        self.stop_virtual_camera()

    def display_info(self, message):
        """Display status messages in the status label."""
        backend = self.vcam_backend_combo.currentData()
        hint = ""
        if backend == "unitycapture":
            hint = " | In OBS: Add → Video Capture Device → 'Unity Video Capture'"
        elif backend == "obs":
            hint = " | In Zoom/Meet: pick 'OBS Virtual Camera' as your camera"
        self.status_label.setText(f"Status: {message}{hint}")
        logging.info(f"Info: {message}")

    def auto_optimize_parameters(self):
        """Intelligently optimize parameters for the current style based on frame analysis."""
        # Ensure there's a frame to optimize on
        if not self.thread or self.thread.last_frame is None:
            show_error_dialog(self, "No frame available for optimization.")
            return
        
        selected_style = self.current_style
        frame = self.thread.last_frame
        
        try:
            # Check if the style has the old ai_optimize method
            if hasattr(selected_style, "ai_optimize"):
                # Use the old AI optimization method
                optimized_params = selected_style.ai_optimize(frame, self.current_style_params.copy())
                if "enable_ai_optimization" in optimized_params:
                    optimized_params["enable_ai_optimization"] = False
            else:
                # Use intelligent parameter optimization for unified styles
                optimized_params = self._intelligent_parameter_optimization(selected_style, frame)
            
            # Update internal state and UI controls
            self.current_style_params = optimized_params
            self.parameter_controls.update_parameters(
                selected_style.parameters,
                self.current_style_params,
                self.on_param_changed
            )
            
            # Save optimized parameters
            style_name = self.style_tab_manager.get_current_style()
            self.settings["parameters"][style_name] = self.current_style_params
            save_settings(self.settings)
            
            # Show detailed optimization results
            param_changes = []
            for key, value in optimized_params.items():
                if key in self.current_style_params and self.current_style_params[key] != value:
                    param_changes.append(f"{key}: {self.current_style_params[key]} → {value}")
            
            if param_changes:
                changes_text = "\n".join(param_changes[:5])  # Show first 5 changes
                if len(param_changes) > 5:
                    changes_text += f"\n... and {len(param_changes) - 5} more changes"
                QMessageBox.information(self, "Auto Optimize", f"Parameters optimized!\n\nChanges made:\n{changes_text}")
            else:
                QMessageBox.information(self, "Auto Optimize", "Parameters were already optimal for this frame.")
            
        except Exception as e:
            show_error_dialog(self, f"Parameter optimization failed: {str(e)}")
            logging.exception("Parameter optimization error")

    def _intelligent_parameter_optimization(self, style, frame):
        """Intelligently optimize parameters based on frame characteristics and style type."""
        import cv2
        import numpy as np
        
        # Start with current parameters
        optimized_params = self.current_style_params.copy()
        
        # Analyze frame characteristics more thoroughly
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        contrast = np.std(gray)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (frame.shape[0] * frame.shape[1])
        
        # Additional analysis
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_peak = np.argmax(hist)
        hist_spread = np.std(hist)
        
        # Style-specific optimizations with more dramatic changes
        style_name = style.name.lower()
        
        if "cartoon" in style_name:
            # More aggressive cartoon optimization
            if brightness < 70:  # Very dark image
                optimized_params["edge_threshold"] = 25
                optimized_params["color_saturation"] = 2.5
                optimized_params["blur_strength"] = 8
            elif brightness > 200:  # Very bright image
                optimized_params["edge_threshold"] = 80
                optimized_params["color_saturation"] = 1.2
                optimized_params["blur_strength"] = 3
            elif brightness < 120:  # Dark image
                optimized_params["edge_threshold"] = 35
                optimized_params["color_saturation"] = 2.0
                optimized_params["blur_strength"] = 6
            elif brightness > 160:  # Bright image
                optimized_params["edge_threshold"] = 70
                optimized_params["color_saturation"] = 1.3
                optimized_params["blur_strength"] = 4
            else:  # Normal brightness
                optimized_params["edge_threshold"] = 50
                optimized_params["color_saturation"] = 1.8
                optimized_params["blur_strength"] = 5
            
            # Adjust based on edge density with more dramatic changes
            if edge_density > 0.15:  # Very high detail
                optimized_params["blur_strength"] = max(2, optimized_params["blur_strength"] - 2)
                optimized_params["edge_threshold"] = max(20, optimized_params["edge_threshold"] - 15)
            elif edge_density < 0.05:  # Very low detail
                optimized_params["blur_strength"] = min(12, optimized_params["blur_strength"] + 3)
                optimized_params["edge_threshold"] = min(100, optimized_params["edge_threshold"] + 20)
            
            # Advanced cartoon specific with more dramatic changes
            if hasattr(style, 'variants') and "Advanced" in style.variants:
                if edge_density > 0.15:
                    optimized_params["detail_level"] = 5
                    optimized_params["smoothness"] = 0.4
                elif edge_density < 0.05:
                    optimized_params["detail_level"] = 1
                    optimized_params["smoothness"] = 1.0
                else:
                    optimized_params["detail_level"] = 3
                    optimized_params["smoothness"] = 0.7
        
        elif "sketch" in style_name:
            # More aggressive sketch optimization
            if contrast < 25:  # Very low contrast
                optimized_params["edge_strength"] = 0.9
                optimized_params["detail_level"] = 1
            elif contrast > 100:  # Very high contrast
                optimized_params["edge_strength"] = 0.2
                optimized_params["detail_level"] = 5
            elif contrast < 40:  # Low contrast
                optimized_params["edge_strength"] = 0.8
                optimized_params["detail_level"] = 2
            elif contrast > 70:  # High contrast
                optimized_params["edge_strength"] = 0.3
                optimized_params["detail_level"] = 4
            else:  # Normal contrast
                optimized_params["edge_strength"] = 0.6
                optimized_params["detail_level"] = 3
            
            # Advanced sketch specific with more dramatic changes
            if hasattr(style, 'variants') and "Advanced" in style.variants:
                if edge_density > 0.15:
                    optimized_params["gaussian_blur"] = 0.5
                    optimized_params["edge_threshold"] = 50
                    optimized_params["contrast_enhancement"] = 2.5
                elif edge_density < 0.05:
                    optimized_params["gaussian_blur"] = 2.5
                    optimized_params["edge_threshold"] = 150
                    optimized_params["contrast_enhancement"] = 1.2
                else:
                    optimized_params["gaussian_blur"] = 1.0
                    optimized_params["edge_threshold"] = 100
                    optimized_params["contrast_enhancement"] = 1.8
        
        elif "edge" in style_name:
            # More aggressive edge detection optimization
            if edge_density > 0.15:  # Very high edge density
                optimized_params["threshold1"] = 30
                optimized_params["threshold2"] = 80
            elif edge_density < 0.05:  # Very low edge density
                optimized_params["threshold1"] = 120
                optimized_params["threshold2"] = 250
            elif edge_density > 0.1:  # High edge density
                optimized_params["threshold1"] = 50
                optimized_params["threshold2"] = 120
            else:  # Low edge density
                optimized_params["threshold1"] = 100
                optimized_params["threshold2"] = 200
            
            # Enhanced edge detection specific with more dramatic changes
            if hasattr(style, 'variants') and "Enhanced" in style.variants:
                if edge_density > 0.15:
                    optimized_params["edge_thickness"] = 3
                    optimized_params["noise_reduction"] = 0.5
                elif edge_density < 0.05:
                    optimized_params["edge_thickness"] = 1
                    optimized_params["noise_reduction"] = 2.5
                else:
                    optimized_params["edge_thickness"] = 2
                    optimized_params["noise_reduction"] = 1.0
        
        # Ensure all parameters are within valid ranges
        for param_name, param_value in optimized_params.items():
            if hasattr(style, 'parameters') and param_name in [p["name"] for p in style.parameters]:
                param_def = next((p for p in style.parameters if p["name"] == param_name), None)
                if param_def:
                    if "min" in param_def:
                        optimized_params[param_name] = max(param_def["min"], param_value)
                    if "max" in param_def:
                        optimized_params[param_name] = min(param_def["max"], param_value)
        
        # Log the optimization for debugging
        logging.info(f"Auto-optimized parameters for {style_name}: {optimized_params}")
        
        return optimized_params

    def closeEvent(self, event):
        """Ensure the thread stops when closing the app."""
        if self.thread and self.thread.isRunning():
            self.thread.stop()
            logging.info("Application closed. WebcamThread stopped.")
        event.accept()

# =============================================================================
# 5. Main Function - App Entry Point
# =============================================================================

def main():
    # Setup logging with rotation
    file_handler = RotatingFileHandler(
        "webcam_app.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.basicConfig(
        level=logging.WARNING,
        handlers=[file_handler, stream_handler]
    )

    app = QApplication(sys.argv)
    window = WebcamApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
