# webcam_filter_pyqt5.py

import inspect
import sys
import os
import json
import subprocess
import warnings

# Suppress PyQt5 deprecation warning for sipPyTypeDict - MUST be before PyQt5 imports
import sys
warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*sipPyTypeDict.*')
warnings.filterwarnings('ignore', message='.*sipPyTypeDict.*')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='sip.*')

import av
import cv2
# Suppress OpenCV warnings immediately after import
# Try to set log level (may not be available in all OpenCV versions)
try:
    # OpenCV 4.x uses these constants
    if hasattr(cv2, 'setLogLevel'):
        # Try different possible constant names
        if hasattr(cv2, 'LOG_LEVEL_ERROR'):
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
        elif hasattr(cv2, 'LOG_LEVEL_SILENT'):
            cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
        else:
            # Try numeric value (4 = ERROR level in OpenCV 4.x)
            cv2.setLogLevel(4)
except (AttributeError, TypeError):
    # If setLogLevel doesn't exist or fails, just use environment variables
    pass

os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

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
# Unified cartoon style with presets
from styles.artistic.cartoon import CartoonStylePro
# from styles.artistic.advanced_cartoon2 import AdvancedCartoonAnime # Removed (consolidated)

# Import the updated WebcamThread
from webcam_threading import WebcamThread  # Ensure this path is correct

# Import enhanced AI optimizer
try:
    from src.gui.modules.enhanced_ai_optimizer import EnhancedAIOptimizer
    ENHANCED_OPTIMIZER_AVAILABLE = True
except ImportError:
    EnhancedAIOptimizer = None
    ENHANCED_OPTIMIZER_AVAILABLE = False
    logging.warning("Enhanced AI optimizer not available, using fallback optimization")

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
        # Add default snapshot directory
        "snapshot_dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snapshots'),
        # 'obs' for Zoom/Meet, 'unitycapture' for ingesting into OBS as a source
        "vcam_backend": "obs"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                default_settings.update(loaded)
        except (json.JSONDecodeError, IOError):
            logging.warning(
                "Failed to load config.json. Using default settings.")
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
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT).decode('utf-8', errors='ignore')
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


def auto_scan_opencv_devices():
    """
    Auto-scan devices using OpenCV (Windows: MSMF backend for index access, Linux/Mac: default).
    Returns a list of working device indices and their names.
    """
    working_devices = []
    try:
        import cv2
        logging.info("Scanning devices using OpenCV...")
        
        # Log available backends
        backends = []
        if hasattr(cv2, 'videoio_registry'):
            backends = cv2.videoio_registry.getBackends()
            logging.info(f"Available OpenCV backends: {backends}")
        else:
            logging.info("OpenCV version doesn't support backend enumeration")
        
        # On Windows, DirectShow doesn't support index-based access well
        # Use MSMF (Media Foundation) which supports index access, or fall back to default
        if os.name == "nt":
            # Try MSMF first (better for index-based access on Windows)
            backend = cv2.CAP_MSMF if hasattr(cv2, 'CAP_MSMF') else cv2.CAP_ANY
            logging.info("Using MSMF backend for Windows (supports index-based access)")
        else:
            backend = cv2.CAP_ANY
        
        # Scan up to 10 device indices
        # Suppress OpenCV warnings during device enumeration
        cv2_log_level = None
        try:
            if hasattr(cv2, 'getLogLevel'):
                cv2_log_level = cv2.getLogLevel()
            if hasattr(cv2, 'setLogLevel'):
                if hasattr(cv2, 'LOG_LEVEL_SILENT'):
                    cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
                else:
                    # Try numeric value (0 = SILENT in OpenCV 4.x)
                    cv2.setLogLevel(0)
        except (AttributeError, TypeError):
            pass
        
        for i in range(10):
            try:
                cap = cv2.VideoCapture(i, backend)
                if cap.isOpened():
                    # Try to read a frame to verify it's actually working
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Try to get device name (may not work on all systems)
                        device_name = f"Device {i}"
                        try:
                            # Some backends support getting device name
                            backend_name = cap.getBackendName()
                            logging.info(f"Device {i}: OpenCV backend={backend_name}, working=True")
                        except:
                            logging.info(f"Device {i}: working=True (backend info unavailable)")
                        
                        working_devices.append({
                            'index': i,
                            'name': device_name,
                            'opencv_index': i,
                            'backend': backend
                        })
                    cap.release()
                else:
                    cap.release()
            except Exception as e:
                # Silently skip devices that fail to open
                logging.debug(f"Device {i} failed to open: {e}")
                continue
        
        # Restore OpenCV log level
        try:
            if cv2_log_level is not None and hasattr(cv2, 'setLogLevel'):
                cv2.setLogLevel(cv2_log_level)
        except (AttributeError, TypeError):
            pass
        
        # If no devices found with MSMF on Windows, try default backend
        if not working_devices and os.name == "nt" and backend != cv2.CAP_ANY:
            logging.info("No devices found with MSMF, trying default backend...")
            for i in range(10):
                try:
                    cap = cv2.VideoCapture(i)  # Default backend
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            working_devices.append({
                                'index': i,
                                'name': f"Device {i}",
                                'opencv_index': i,
                                'backend': cv2.CAP_ANY
                            })
                            logging.info(f"Device {i}: Found with default backend")
                        cap.release()
                    else:
                        cap.release()
                except Exception as e:
                    logging.debug(f"Device {i} scan with default backend failed: {e}")
                    continue
        
        if working_devices:
            logging.info(f"Found {len(working_devices)} working OpenCV device(s)")
        else:
            logging.warning("No working OpenCV devices found")
            
    except ImportError:
        logging.warning("OpenCV not available for device scanning")
    except Exception as e:
        logging.error(f"Error during OpenCV device scan: {e}")
    
    return working_devices


def find_working_device(device_name=None):
    """
    Auto-detect and return a working device.
    Tries multiple methods:
    1. FFmpeg DirectShow enumeration (by name)
    2. OpenCV DirectShow index scanning
    3. Fallback to first available
    
    Returns: (device_string, method_used)
    """
    logging.info("=== Starting device auto-detection ===")
    
    # Method 1: Try FFmpeg DirectShow enumeration
    ffmpeg_devices = list_devices()
    if ffmpeg_devices:
        logging.info(f"FFmpeg found {len(ffmpeg_devices)} device(s): {ffmpeg_devices}")
        
        # If device_name specified, try to match it
        if device_name:
            # Remove 'video=' prefix if present
            search_name = device_name.replace('video=', '').strip()
            for dev in ffmpeg_devices:
                dev_name = dev.replace('video=', '').strip()
                if search_name.lower() in dev_name.lower() or dev_name.lower() in search_name.lower():
                    logging.info(f"Matched device by name: {dev}")
                    return dev, "ffmpeg_name_match"
            
            # If no match, try first device
            if ffmpeg_devices:
                logging.info(f"Using first FFmpeg device: {ffmpeg_devices[0]}")
                return ffmpeg_devices[0], "ffmpeg_first"
        else:
            # No device specified, use first available
            logging.info(f"Using first FFmpeg device: {ffmpeg_devices[0]}")
            return ffmpeg_devices[0], "ffmpeg_first"
    
    # Method 2: Try OpenCV DirectShow index scanning
    logging.info("Trying OpenCV DirectShow index scanning...")
    opencv_devices = auto_scan_opencv_devices()
    if opencv_devices:
        # Use first working OpenCV device
        idx = opencv_devices[0]['opencv_index']
        # For PyAV, we'll need to convert index to device name
        # But first, let's try using the index directly with a fallback format
        device_str = f"video={opencv_devices[0]['name']}"
        logging.info(f"Using OpenCV device index {idx}: {device_str}")
        return device_str, "opencv_index"
    
    # Method 3: Fallback - try common device names
    logging.warning("No devices found via FFmpeg or OpenCV. Trying fallback...")
    fallback_names = [
        "video=C270 HD WEBCAM",
        "video=Logitech HD Webcam C270",
        "video=USB2.0 Camera",
        "video=Integrated Camera"
    ]
    
    for fallback in fallback_names:
        logging.info(f"Trying fallback device: {fallback}")
        # We'll let PyAV/OpenCV try to open it
        return fallback, "fallback"
    
    # Last resort: return None and let the error handler deal with it
    logging.error("No devices found via any method")
    return None, "none"

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
                        if getattr(cls, "__skip_registration__", False):
                            logging.debug(
                                f"Skipping legacy style class {cls.__module__}.{cls.__name__}")
                            continue
                        try:
                            instance = cls()  # Instantiate
                            seen_classes.add(cls)

                            category = getattr(
                                instance, "category", "Uncategorized")
                            if category not in style_categories:
                                style_categories[category] = []

                            # Avoid duplicate style names in the same category
                            if instance.name not in style_categories[category]:
                                style_categories[category].append(
                                    instance.name)

                            style_instances[instance.name] = instance
                            logging.info(
                                f"Loaded style: {instance.name} (Category: {category})")

                        except Exception as instantiation_error:
                            logging.error(
                                f"Failed to instantiate style '{cls.__name__}': {instantiation_error}")

            except Exception as module_error:
                logging.error(
                    f"Failed to load module '{modname}': {module_error}")

    return style_instances, style_categories

# =============================================================================
# 4. PyQt5 GUI
# =============================================================================


# Debug mode flag (can be set via config or env)
DEBUG_MODE = os.environ.get("METUBER_DEBUG", "0") == "1"

SNAPSHOT_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'snapshots')
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

        # Enhanced AI optimizer
        if ENHANCED_OPTIMIZER_AVAILABLE:
            try:
                self.enhanced_optimizer = EnhancedAIOptimizer()
                logging.info("✅ Enhanced AI optimizer initialized")
            except Exception as e:
                logging.warning(f"Could not initialize enhanced optimizer: {e}")
                self.enhanced_optimizer = None
        else:
            self.enhanced_optimizer = None

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
            style_params = self.settings.get(
                "parameters", {}).get(style_name, {})
            try:
                # Guard against missing validate_params method
                if hasattr(style_instance, 'validate_params'):
                    validated_params = style_instance.validate_params(
                        style_params)
                else:
                    # Fallback: build defaults from parameters
                    validated_params = {
                        param['name']: style_params.get(
                            param['name'], param.get("default", 0))
                        for param in style_instance.parameters
                    }
            except AttributeError as e:
                # Handle styles missing expected attributes (like current_variant)
                logging.warning(
                    f"Invalid parameters for style '{style_name}': {e}. Resetting to defaults.")
                validated_params = {
                    param['name']: param.get("default", 0)
                    for param in style_instance.parameters
                }
            except Exception as e:
                logging.warning(
                    f"Invalid parameters for style '{style_name}': {e}. Resetting to defaults.")
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
                        # Empty path = disabled feature
                        validated_params[param['name']] = ""
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
        self.preview_label.setObjectName(
            "Filtered Preview")  # stable name for OBS picker
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background:#111; color:#aaa; padding:8px;")
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
        
        # Add OpenCV-scanned devices as fallback options
        opencv_devices = auto_scan_opencv_devices()
        for ocv_dev in opencv_devices:
            # Format as "video=Device X (OpenCV Index N)"
            device_str = f"video=Device {ocv_dev['index']} (OpenCV Index {ocv_dev['opencv_index']})"
            if device_str not in devices:
                devices.append(device_str)
        
        if not devices or devices == ["Enter device manually..."]:
            devices = ["Enter device manually...", "Auto-detect on start"]
        else:
            devices.insert(0, "Auto-detect on start")
        
        default_device = self.settings.get(
            "input_device", devices[0] if devices else "")
        device_selector = DeviceSelector(self, devices, default_device)
        layout.addLayout(device_selector.create())
        self.device_combo = device_selector.device_combo

        # 1.5) Output / Virtual Camera Settings
        out_group = QGroupBox("Output")
        out_form = QFormLayout()
        self.vcam_backend_combo = QComboBox()
        # Human labels → backend ids
        self.vcam_backend_combo.addItem(
            "OBS Virtual Camera (for Zoom/Meet/Teams)", userData="obs")
        self.vcam_backend_combo.addItem(
            "UnityCapture (add as 'Video Capture Device' in OBS)", userData="unitycapture")
        # Restore from settings
        backend_default = self.settings.get("vcam_backend", "obs")
        idx = max(0, self.vcam_backend_combo.findData(backend_default))
        self.vcam_backend_combo.setCurrentIndex(idx)
        out_form.addRow("Virtual Cam Backend:", self.vcam_backend_combo)
        out_group.setLayout(out_form)
        layout.addWidget(out_group)

        # 2) Style Selector with Categories
        style_tab_manager = StyleTabManager(
            self, self.style_categories, self.style_instances, self.settings)
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
        self.vcam_toggle = QCheckBox(
            "Send frames to Virtual Camera (OBS backend)")
        self.vcam_toggle.setChecked(True)
        layout.addWidget(self.vcam_toggle)

        # 4.1) Auto Optimize Parameters Button
        self.optimize_button = QPushButton("Auto Optimize Parameters")
        self.optimize_button.clicked.connect(self.auto_optimize_parameters)
        layout.addWidget(self.optimize_button)
        # 4.2) Set Snapshot Directory Button
        self.set_snapshot_dir_button = QPushButton("Set Snapshot Save Folder")
        self.set_snapshot_dir_button.clicked.connect(
            self.set_snapshot_directory)
        layout.addWidget(self.set_snapshot_dir_button)

        # 4.3) Performance Controls
        performance_group = QGroupBox("Performance Settings")
        performance_layout = QFormLayout()

        # Max FPS slider
        self.max_fps_slider = QSlider(Qt.Horizontal)
        self.max_fps_slider.setRange(1, 60)
        self.max_fps_slider.setValue(30)
        self.max_fps_label = QLabel("30")
        self.max_fps_slider.valueChanged.connect(
            lambda v: self.max_fps_label.setText(str(v)))
        performance_layout.addRow("Max FPS:", self.max_fps_slider)
        performance_layout.addRow("", self.max_fps_label)

        # Frame skip slider
        self.frame_skip_slider = QSlider(Qt.Horizontal)
        self.frame_skip_slider.setRange(0, 10)
        self.frame_skip_slider.setValue(0)
        self.frame_skip_label = QLabel("0")
        self.frame_skip_slider.valueChanged.connect(
            lambda v: self.frame_skip_label.setText(str(v)))
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
            # Handle both grayscale (2D) and color (3D) images
            if len(bgr.shape) == 2:
                # Convert grayscale to BGR
                bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
            elif len(bgr.shape) == 3 and bgr.shape[2] == 1:
                # Convert single channel to BGR
                bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
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
        self.current_style = self.style_instances.get(
            selected_style_name, Original())

        saved_params = self.settings.get("parameters", {})
        self.current_style_params = saved_params.get(
            selected_style_name, {}).copy()

        if self.current_style:
            logging.info(
                f"Updating parameters for style: {selected_style_name}")

            # Ensure all parameters have default values if missing
            for param in self.current_style.parameters:
                if param["name"] not in self.current_style_params:
                    self.current_style_params[param["name"]] = param.get(
                        "default", 0)
            # For 'file' parameters, if the path no longer exists (e.g. file moved), reset to default to update GUI
            for param in self.current_style.parameters:
                if param.get("type") == "file":
                    current_path = self.current_style_params.get(
                        param["name"], "")
                    if current_path and not os.path.exists(current_path):
                        logging.info(
                            f"File for parameter '{param['name']}' not found at '{current_path}', resetting to default '{param.get('default','')}'"
                        )
                        # Reset internal state and update settings
                        new_default = param.get('default', '')
                        self.current_style_params[param['name']] = new_default
                        # Persist change
                        style_name = self.style_tab_manager.get_current_style()
                        self.settings['parameters'][style_name][param['name']
                                                                ] = new_default
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
                logging.error(
                    f"Failed to update label for '{param_name}': {e}")
        elif isinstance(widget, QComboBox):
            logging.debug(f"ComboBox '{param_name}' changed to '{value}'")
        elif isinstance(widget, QCheckBox):
            logging.debug(f"Checkbox '{param_name}' changed to '{value}'")
        else:
            logging.debug(
                f"Parameter '{param_name}' updated to {value} (widget={type(widget)})")

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

        # Auto-detect device if not specified or if "Enter device manually..." or "Auto-detect on start" is selected
        if not input_device or input_device == "Enter device manually..." or input_device == "Auto-detect on start":
            logging.info("No device specified or auto-detect requested, attempting auto-detection...")
            detected_device, method = find_working_device()
            if detected_device:
                input_device = detected_device
                logging.info(f"Auto-detected device: {input_device} (method: {method})")
                # Update the combo box to show the detected device
                if detected_device in [self.device_combo.itemText(i) for i in range(self.device_combo.count())]:
                    self.device_combo.setCurrentText(detected_device)
                else:
                    self.device_combo.addItem(detected_device)
                    self.device_combo.setCurrentText(detected_device)
            else:
                QMessageBox.warning(
                    self, "Input Device Error",
                    "No camera device found.\n\n"
                    "Please check:\n"
                    "1. Camera is connected\n"
                    "2. Windows Camera privacy settings are enabled\n"
                    "3. No other apps are using the camera\n"
                    "4. Camera drivers are installed"
                )
                return

        # Convert device name to PyAV-compatible format
        pyav_device = convert_device_name_for_pyav(input_device)
        if not pyav_device:
            # Try auto-detection as fallback
            logging.warning(f"Invalid device format '{input_device}', trying auto-detection...")
            detected_device, method = find_working_device(input_device)
            if detected_device:
                pyav_device = convert_device_name_for_pyav(detected_device)
                logging.info(f"Auto-detected fallback device: {pyav_device} (method: {method})")
            else:
                QMessageBox.warning(
                    self, "Input Device Error",
                    f"Invalid device name format: '{input_device}'\n\n"
                    "Attempted auto-detection but no working devices found.\n\n"
                    "Please check:\n"
                    "1. Camera is connected\n"
                    "2. Windows Camera privacy settings are enabled\n"
                    "3. No other apps are using the camera"
                )
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
            QMessageBox.warning(self, "Style Selection Error",
                                "Please select a style.")
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
        self.thread.frame_signal.connect(
            self._show_bgr_on_preview)  # ✅ live preview
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
            # Disconnect signals to prevent memory leaks
            try:
                self.thread.error_signal.disconnect()
                self.thread.info_signal.disconnect()
                self.thread.frame_signal.disconnect()
            except (TypeError, RuntimeError):
                # Signals may not be connected or already disconnected
                pass
            
            self.thread.stop()
            # Wait for thread to finish (with timeout)
            if self.thread.isRunning():
                self.thread.wait(3000)  # Wait up to 3 seconds
                if self.thread.isRunning():
                    logging.warning("Thread did not stop within timeout, terminating...")
                    self.thread.terminate()
                    self.thread.wait(1000)  # Wait for termination
            self.thread = None
            self.status_label.setText("Status: Stopped")
            logging.info("Virtual camera stopped.")

        # Update button states
        self.action_buttons.start_button.setEnabled(True)
        self.action_buttons.stop_button.setEnabled(False)
        self.action_buttons.snapshot_button.setEnabled(False)

    def set_snapshot_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Snapshot Save Folder", self.snapshot_dir)
        if dir_path:
            self.snapshot_dir = dir_path
            self.settings['snapshot_dir'] = dir_path
            save_settings(self.settings)

    def take_snapshot(self):
        """Capture the last processed frame and let the user save it."""
        if not self.thread or self.thread.last_frame is None:
            QMessageBox.information(
                self, "Snapshot", "No frame available to save.")
            return
        default_path = os.path.join(self.snapshot_dir, "snapshot.png")
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Snapshot", default_path, "Image Files (*.png *.jpg *.bmp)")
        if save_path:
            cv2.imwrite(save_path, self.thread.last_frame)
            QMessageBox.information(
                self, "Snapshot", f"Snapshot saved to:\n{save_path}")
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
        """
        Intelligently optimize parameters for the current style based on comprehensive frame analysis.
        Uses enhanced AI optimizer with quality validation when available.
        """
        # Ensure there's a frame to optimize on
        if not self.thread or self.thread.last_frame is None:
            show_error_dialog(self, "No frame available for optimization.\n\nPlease start the camera first.")
            return

        selected_style = self.current_style
        frame = self.thread.last_frame
        
        # Store original parameters for comparison
        original_params = self.current_style_params.copy()

        try:
            # Show progress
            self.status_label.setText("Status: Analyzing frame and optimizing parameters...")
            QApplication.processEvents()  # Update UI
            
            # Try enhanced optimizer first (with validation)
            if self.enhanced_optimizer and selected_style:
                try:
                    # Create filter application function
                    def apply_filter(params, input_frame):
                        """Apply style with given parameters."""
                        try:
                            # Create temporary style instance
                            temp_style = selected_style.__class__()
                            # Apply parameters
                            for key, value in params.items():
                                if hasattr(temp_style, key):
                                    setattr(temp_style, key, value)
                            # Apply filter
                            return temp_style.apply(input_frame.copy())
                        except Exception as e:
                            logging.error(f"Error applying filter in optimizer: {e}")
                            return input_frame
                    
                    # Run enhanced optimization with validation
                    style_name = selected_style.name if hasattr(selected_style, 'name') else str(selected_style.__class__.__name__)
                    result = self.enhanced_optimizer.optimize_with_validation(
                        style_name=style_name,
                        current_params=original_params.copy(),
                        frame=frame.copy(),
                        apply_filter=apply_filter,
                        optimization_method="grid_search",
                        max_iterations=50
                    )
                    
                    # Check if optimization improved quality
                    if result.improvement > 0:
                        optimized_params = result.parameters
                        self._show_enhanced_optimization_results(result, original_params, selected_style)
                    else:
                        # No significant improvement, use fallback
                        logging.info("Enhanced optimizer found no improvement, using fallback")
                        optimized_params = self._get_fallback_optimization(selected_style, frame)
                except Exception as e:
                    logging.warning(f"Enhanced optimizer failed, using fallback: {e}")
                    optimized_params = self._get_fallback_optimization(selected_style, frame)
            else:
                # Fallback to original optimization methods
                optimized_params = self._get_fallback_optimization(selected_style, frame)
            
            # Analyze what changed
            param_changes = []
            significant_changes = []
            
            # Check all parameters in optimized_params
            for key, new_value in optimized_params.items():
                old_value = original_params.get(key)
                # Handle both cases: parameter existed before or is new
                if old_value is None:
                    # New parameter was added
                    param_changes.append((key, "default", new_value))
                elif old_value != new_value:
                    # Parameter was changed
                    # Calculate change percentage for numeric values
                    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                        if old_value != 0:
                            change_pct = abs((new_value - old_value) / old_value) * 100
                        else:
                            change_pct = 100 if new_value != 0 else 0
                        
                        if change_pct > 10:  # Significant change (>10%)
                            significant_changes.append((key, old_value, new_value, change_pct))
                    elif isinstance(old_value, str) or isinstance(new_value, str):
                        # String parameters (like preset names)
                        change_pct = 100 if old_value != new_value else 0
                        if change_pct > 0:
                            significant_changes.append((key, old_value, new_value, change_pct))
                    
                    param_changes.append((key, old_value, new_value))
            
            # Update internal state and UI controls
            self.current_style_params = optimized_params
            self.parameter_controls.update_parameters(
                selected_style.parameters,
                self.current_style_params,
                self.on_param_changed
            )
            
            # Update thread parameters if running
            if self.thread and self.thread.isRunning():
                thread_params = dict(self.current_style_params)
                thread_params['max_fps'] = self.max_fps_slider.value()
                thread_params['frame_skip'] = self.frame_skip_slider.value()
                self.thread.update_params(thread_params)

            # Save optimized parameters
            style_name = self.style_tab_manager.get_current_style()
            self.settings["parameters"][style_name] = self.current_style_params
            save_settings(self.settings)

            # Show detailed optimization results
            if param_changes:
                # Build detailed message
                changes_text = "Optimization complete! The following parameters were adjusted:\n\n"
                
                # Show significant changes first
                if significant_changes:
                    changes_text += "Major adjustments (>10% change):\n"
                    for key, old_val, new_val, pct in significant_changes[:5]:
                        param_label = next((p.get('label', key) for p in selected_style.parameters if p['name'] == key), key)
                        if isinstance(old_val, float) and isinstance(new_val, float):
                            changes_text += f"  • {param_label}: {old_val:.2f} → {new_val:.2f} ({pct:.0f}% change)\n"
                        else:
                            changes_text += f"  • {param_label}: {old_val} → {new_val} ({pct:.0f}% change)\n"
                    changes_text += "\n"
                
                # Show other changes
                other_changes = [c for c in param_changes if not any(c[0] == sc[0] for sc in significant_changes)]
                if other_changes:
                    changes_text += "Other adjustments:\n"
                    for change in other_changes[:5]:
                        key, old_val, new_val = change[0], change[1], change[2]
                        param_label = next((p.get('label', key) for p in selected_style.parameters if p['name'] == key), key)
                        if old_val == "default":
                            if isinstance(new_val, float):
                                changes_text += f"  • {param_label}: set to {new_val:.2f}\n"
                            else:
                                changes_text += f"  • {param_label}: set to {new_val}\n"
                        elif isinstance(old_val, float) and isinstance(new_val, float):
                            changes_text += f"  • {param_label}: {old_val:.2f} → {new_val:.2f}\n"
                        else:
                            changes_text += f"  • {param_label}: {old_val} → {new_val}\n"
                
                if len(param_changes) > 10:
                    changes_text += f"\n... and {len(param_changes) - 10} more minor adjustments"
                
                changes_text += "\n\nFrame analysis detected:"
                analysis = self._analyze_frame_comprehensive(frame)
                changes_text += f"\n  • Brightness: {analysis['brightness_category']} ({analysis['brightness']:.0f}/255)"
                changes_text += f"\n  • Contrast: {analysis['contrast_category']} ({analysis['contrast']:.1f})"
                changes_text += f"\n  • Detail level: {analysis['detail_level']} (edge density: {analysis['edge_density']:.1%})"
                changes_text += f"\n  • Texture: {'sharp' if analysis['texture_sharpness'] > 0.5 else 'soft'}"
                
                QMessageBox.information(
                    self, "Auto Optimize - Complete", changes_text)
                self.status_label.setText("Status: Parameters optimized successfully")
            else:
                QMessageBox.information(
                    self, "Auto Optimize", 
                    "Parameters were already well-optimized for this frame.\n\n"
                    "No adjustments were needed based on the current frame analysis.")

        except Exception as e:
            show_error_dialog(self, f"Parameter optimization failed: {str(e)}")
            logging.exception("Parameter optimization error")
            self.status_label.setText("Status: Optimization failed - see error message")

    def _analyze_frame_comprehensive(self, frame):
        """
        Comprehensive frame analysis for intelligent parameter optimization.
        Returns a dictionary with various frame characteristics.
        """
        import cv2
        import numpy as np
        
        analysis = {}
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        total_pixels = h * w
        
        # Basic statistics
        analysis['brightness'] = np.mean(gray)  # 0-255
        analysis['brightness_normalized'] = analysis['brightness'] / 255.0  # 0-1
        analysis['contrast'] = np.std(gray)  # Standard deviation
        analysis['contrast_normalized'] = analysis['contrast'] / 128.0  # Rough normalization
        
        # Histogram analysis
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_peak = np.argmax(hist)
        hist_spread = np.std(hist)
        analysis['histogram_peak'] = hist_peak
        analysis['histogram_spread'] = hist_spread
        analysis['histogram_skew'] = np.sum(hist * (np.arange(256) - analysis['brightness'])) / (total_pixels * analysis['contrast'] + 1e-6)
        
        # Edge analysis
        edges_canny = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges_canny > 0) / total_pixels
        analysis['edge_density'] = edge_density
        
        # Texture analysis using Laplacian variance (blur detection)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        analysis['texture_variance'] = laplacian.var()
        analysis['texture_sharpness'] = min(1.0, analysis['texture_variance'] / 1000.0)  # Normalized
        
        # Color analysis
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        analysis['saturation'] = np.mean(hsv[:, :, 1]) / 255.0  # 0-1
        analysis['hue_variance'] = np.std(hsv[:, :, 0]) / 180.0  # Normalized
        
        # Noise estimation (using high-frequency content)
        kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
        high_freq = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        analysis['noise_level'] = min(1.0, np.std(high_freq) / 50.0)  # Normalized
        
        # Detail level classification
        if edge_density > 0.15:
            analysis['detail_level'] = 'very_high'
        elif edge_density > 0.1:
            analysis['detail_level'] = 'high'
        elif edge_density > 0.05:
            analysis['detail_level'] = 'medium'
        else:
            analysis['detail_level'] = 'low'
        
        # Brightness classification
        if analysis['brightness'] < 70:
            analysis['brightness_category'] = 'very_dark'
        elif analysis['brightness'] < 120:
            analysis['brightness_category'] = 'dark'
        elif analysis['brightness'] > 200:
            analysis['brightness_category'] = 'very_bright'
        elif analysis['brightness'] > 160:
            analysis['brightness_category'] = 'bright'
        else:
            analysis['brightness_category'] = 'normal'
        
        # Contrast classification
        if analysis['contrast'] < 25:
            analysis['contrast_category'] = 'very_low'
        elif analysis['contrast'] < 40:
            analysis['contrast_category'] = 'low'
        elif analysis['contrast'] > 100:
            analysis['contrast_category'] = 'very_high'
        elif analysis['contrast'] > 70:
            analysis['contrast_category'] = 'high'
        else:
            analysis['contrast_category'] = 'normal'
        
        return analysis

    def _intelligent_parameter_optimization(self, style, frame):
        """
        Intelligently optimize parameters based on comprehensive frame analysis.
        Works with any style by analyzing parameter names and types.
        """
        import cv2
        import numpy as np

        # Start with current parameters
        optimized_params = self.current_style_params.copy()
        
        # Comprehensive frame analysis
        analysis = self._analyze_frame_comprehensive(frame)
        
        # Get style parameters
        style_params = getattr(style, 'parameters', [])
        param_map = {p['name']: p for p in style_params}
        
        # Style-specific optimizations
        style_name = style.name.lower()
        
        # Cartoon style optimization
        if "cartoon" in style_name:
            self._optimize_cartoon_parameters(optimized_params, analysis, param_map)
        
        # Sketch style optimization
        elif "sketch" in style_name or "pencil" in style_name:
            self._optimize_sketch_parameters(optimized_params, analysis, param_map)
        
        # Edge detection optimization
        elif "edge" in style_name or "line" in style_name:
            self._optimize_edge_parameters(optimized_params, analysis, param_map)
        
        # Generic optimization for other styles
        else:
            self._optimize_generic_parameters(optimized_params, analysis, param_map)
        
        # Ensure all parameters are within valid ranges
        for param_name, param_value in optimized_params.items():
            if param_name in param_map:
                param_def = param_map[param_name]
                if "min" in param_def:
                    optimized_params[param_name] = max(param_def["min"], param_value)
                if "max" in param_def:
                    optimized_params[param_name] = min(param_def["max"], param_value)
        
        # Log the optimization for debugging
        logging.info(f"Auto-optimized parameters for {style_name}: {optimized_params}")
        
        return optimized_params
    
    def _get_fallback_optimization(self, selected_style, frame):
        """Fallback optimization using original methods."""
        # Check if the style has the old ai_optimize method
        if hasattr(selected_style, "ai_optimize"):
            # Use the old AI optimization method
            optimized_params = selected_style.ai_optimize(
                frame, self.current_style_params.copy())
            if "enable_ai_optimization" in optimized_params:
                optimized_params["enable_ai_optimization"] = False
        else:
            # Use intelligent parameter optimization for unified styles
            optimized_params = self._intelligent_parameter_optimization(
                selected_style, frame)
        return optimized_params
    
    def _show_enhanced_optimization_results(self, result, original_params, selected_style):
        """Show results from enhanced optimizer."""
        try:
            # Build results message
            changes_text = "✅ Enhanced Auto-Optimize Complete!\n\n"
            changes_text += f"Quality Score: {result.quality_score:.3f}\n"
            changes_text += f"Improvement: +{result.improvement*100:.1f}%\n\n"
            
            # Show quality metrics
            changes_text += "Quality Metrics:\n"
            for metric_name, metric_value in result.metrics.items():
                if metric_name != 'total':
                    changes_text += f"  • {metric_name.replace('_', ' ').title()}: {metric_value:.3f}\n"
            
            # Show parameter changes
            param_changes = []
            for key, new_value in result.parameters.items():
                old_value = original_params.get(key)
                if old_value != new_value:
                    param_label = next(
                        (p.get('label', key) for p in selected_style.parameters 
                         if p['name'] == key), key
                    ) if hasattr(selected_style, 'parameters') else key
                    param_changes.append((param_label, old_value, new_value))
            
            if param_changes:
                changes_text += "\nParameter Adjustments:\n"
                for label, old_val, new_val in param_changes[:10]:
                    if isinstance(old_val, float) and isinstance(new_val, float):
                        changes_text += f"  • {label}: {old_val:.2f} → {new_val:.2f}\n"
                    else:
                        changes_text += f"  • {label}: {old_val} → {new_val}\n"
            
            QMessageBox.information(self, "Enhanced Auto-Optimize", changes_text)
        except Exception as e:
            logging.error(f"Error showing enhanced optimization results: {e}")
    
    def _optimize_cartoon_parameters(self, params, analysis, param_map):
        """Optimize cartoon-style parameters based on frame analysis."""
        brightness = analysis['brightness']
        edge_density = analysis['edge_density']
        contrast = analysis['contrast']
        texture_sharpness = analysis['texture_sharpness']
        
        # Optimize bilateral filter parameters
        if 'bilateral_sigmaColor' in param_map:
            if brightness < 70:  # Very dark
                params['bilateral_sigmaColor'] = min(200, params.get('bilateral_sigmaColor', 75) + 50)
            elif brightness > 200:  # Very bright
                params['bilateral_sigmaColor'] = max(1, params.get('bilateral_sigmaColor', 75) - 30)
            else:
                params['bilateral_sigmaColor'] = 75 + int((brightness - 128) * 0.3)
        
        if 'bilateral_sigmaSpace' in param_map:
            params['bilateral_sigmaSpace'] = params.get('bilateral_sigmaColor', 75)
        
        if 'bilateral_passes' in param_map:
            if texture_sharpness < 0.3:  # Blurry image
                params['bilateral_passes'] = min(4, params.get('bilateral_passes', 1) + 1)
            elif texture_sharpness > 0.7:  # Sharp image
                params['bilateral_passes'] = max(0, params.get('bilateral_passes', 1) - 1)
        
        # Optimize quantization
        if 'bits' in param_map:
            if edge_density > 0.15:  # High detail
                params['bits'] = max(2, min(8, params.get('bits', 4) + 1))
            elif edge_density < 0.05:  # Low detail
                params['bits'] = max(2, params.get('bits', 4) - 1)
        
        if 'downscale_factor' in param_map:
            if edge_density > 0.15:  # High detail - less downscaling
                params['downscale_factor'] = min(1.0, params.get('downscale_factor', 0.5) + 0.1)
            elif edge_density < 0.05:  # Low detail - more downscaling
                params['downscale_factor'] = max(0.1, params.get('downscale_factor', 0.5) - 0.1)
        
        # Optimize edge detection
        if 'canny_t1' in param_map:
            if edge_density > 0.15:  # High detail - lower thresholds
                params['canny_t1'] = max(0, params.get('canny_t1', 100) - 30)
            elif edge_density < 0.05:  # Low detail - higher thresholds
                params['canny_t1'] = min(500, params.get('canny_t1', 100) + 40)
            else:
                # Adaptive based on brightness
                params['canny_t1'] = int(50 + (brightness / 255.0) * 100)
        
        if 'canny_t2' in param_map:
            if 'canny_t1' in params:
                params['canny_t2'] = params['canny_t1'] * 2
            else:
                if edge_density > 0.15:
                    params['canny_t2'] = max(0, params.get('canny_t2', 200) - 50)
                elif edge_density < 0.05:
                    params['canny_t2'] = min(500, params.get('canny_t2', 200) + 80)
        
        if 'adaptive_C' in param_map:
            if contrast < 25:  # Low contrast
                params['adaptive_C'] = max(-20, params.get('adaptive_C', 2) - 3)
            elif contrast > 100:  # High contrast
                params['adaptive_C'] = min(20, params.get('adaptive_C', 2) + 3)
        
        # Optimize edge morphology
        if 'edge_dilate' in param_map:
            if edge_density < 0.05:  # Low detail - dilate more
                params['edge_dilate'] = min(3, params.get('edge_dilate', 0) + 1)
            elif edge_density > 0.15:  # High detail - dilate less
                params['edge_dilate'] = max(0, params.get('edge_dilate', 0) - 1)
    
    def _optimize_sketch_parameters(self, params, analysis, param_map):
        """Optimize sketch-style parameters based on frame analysis."""
        contrast = analysis['contrast']
        edge_density = analysis['edge_density']
        brightness = analysis['brightness']
        
        # Optimize edge strength/threshold
        for param_name in ['edge_strength', 'edge_threshold', 'threshold']:
            if param_name in param_map:
                if contrast < 25:  # Very low contrast
                    if param_map[param_name].get('type') == 'float':
                        params[param_name] = min(1.0, params.get(param_name, 0.5) + 0.3)
                    else:
                        params[param_name] = min(500, params.get(param_name, 100) + 50)
                elif contrast > 100:  # Very high contrast
                    if param_map[param_name].get('type') == 'float':
                        params[param_name] = max(0.0, params.get(param_name, 0.5) - 0.3)
                    else:
                        params[param_name] = max(0, params.get(param_name, 100) - 50)
        
        # Optimize blur
        for param_name in ['blur_intensity', 'gaussian_blur', 'blur_strength']:
            if param_name in param_map:
                if edge_density > 0.15:  # High detail - less blur
                    if param_map[param_name].get('type') == 'float':
                        params[param_name] = max(0.0, params.get(param_name, 1.0) - 0.3)
                    else:
                        params[param_name] = max(0, params.get(param_name, 5) - 2)
                elif edge_density < 0.05:  # Low detail - more blur
                    if param_map[param_name].get('type') == 'float':
                        params[param_name] = min(5.0, params.get(param_name, 1.0) + 0.5)
                    else:
                        params[param_name] = min(20, params.get(param_name, 5) + 3)
        
        # Optimize detail level
        if 'detail_level' in param_map:
            if edge_density > 0.15:
                params['detail_level'] = min(5, params.get('detail_level', 3) + 2)
            elif edge_density < 0.05:
                params['detail_level'] = max(1, params.get('detail_level', 3) - 2)
    
    def _optimize_edge_parameters(self, params, analysis, param_map):
        """Optimize edge detection parameters based on frame analysis."""
        edge_density = analysis['edge_density']
        contrast = analysis['contrast']
        
        # Optimize thresholds
        if 'threshold1' in param_map:
            if edge_density > 0.15:  # High edge density
                params['threshold1'] = max(0, params.get('threshold1', 100) - 50)
            elif edge_density < 0.05:  # Low edge density
                params['threshold1'] = min(500, params.get('threshold1', 100) + 60)
        
        if 'threshold2' in param_map:
            if 'threshold1' in params:
                params['threshold2'] = params['threshold1'] * 2.5
            else:
                if edge_density > 0.15:
                    params['threshold2'] = max(0, params.get('threshold2', 200) - 70)
                elif edge_density < 0.05:
                    params['threshold2'] = min(500, params.get('threshold2', 200) + 100)
        
        # Optimize edge thickness
        if 'edge_thickness' in param_map:
            if edge_density > 0.15:
                params['edge_thickness'] = min(5, params.get('edge_thickness', 2) + 1)
            elif edge_density < 0.05:
                params['edge_thickness'] = max(1, params.get('edge_thickness', 2) - 1)
        
        # Optimize noise reduction
        if 'noise_reduction' in param_map:
            noise_level = analysis['noise_level']
            if noise_level > 0.5:  # High noise
                if param_map['noise_reduction'].get('type') == 'float':
                    params['noise_reduction'] = min(5.0, params.get('noise_reduction', 1.0) + 1.0)
                else:
                    params['noise_reduction'] = min(10, params.get('noise_reduction', 3) + 2)
            elif noise_level < 0.2:  # Low noise
                if param_map['noise_reduction'].get('type') == 'float':
                    params['noise_reduction'] = max(0.0, params.get('noise_reduction', 1.0) - 0.5)
                else:
                    params['noise_reduction'] = max(0, params.get('noise_reduction', 3) - 1)
    
    def _optimize_generic_parameters(self, params, analysis, param_map):
        """Generic optimization for styles without specific rules."""
        # Try to intelligently map common parameter names
        brightness = analysis['brightness']
        contrast = analysis['contrast']
        edge_density = analysis['edge_density']
        
        # Map common parameter patterns
        param_mappings = {
            'threshold': 'edge_density',
            'strength': 'edge_density',
            'intensity': 'edge_density',
            'blur': 'texture_sharpness',
            'smooth': 'texture_sharpness',
            'saturation': 'saturation',
            'brightness': 'brightness_normalized',
            'contrast': 'contrast_normalized',
        }
        
        for param_name, param_def in param_map.items():
            param_type = param_def.get('type', 'int')
            param_lower = param_name.lower()
            
            # Try to find a mapping
            for pattern, analysis_key in param_mappings.items():
                if pattern in param_lower:
                    value = analysis[analysis_key]
                    
                    # Scale to parameter range
                    if 'min' in param_def and 'max' in param_def:
                        min_val = param_def['min']
                        max_val = param_def['max']
                        if param_type == 'float':
                            params[param_name] = min_val + value * (max_val - min_val)
                        else:
                            params[param_name] = int(min_val + value * (max_val - min_val))
                    break

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
                optimized_params["blur_strength"] = max(
                    2, optimized_params["blur_strength"] - 2)
                optimized_params["edge_threshold"] = max(
                    20, optimized_params["edge_threshold"] - 15)
            elif edge_density < 0.05:  # Very low detail
                optimized_params["blur_strength"] = min(
                    12, optimized_params["blur_strength"] + 3)
                optimized_params["edge_threshold"] = min(
                    100, optimized_params["edge_threshold"] + 20)

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
                param_def = next(
                    (p for p in style.parameters if p["name"] == param_name), None)
                if param_def:
                    if "min" in param_def:
                        optimized_params[param_name] = max(
                            param_def["min"], param_value)
                    if "max" in param_def:
                        optimized_params[param_name] = min(
                            param_def["max"], param_value)

        # Log the optimization for debugging
        logging.info(
            f"Auto-optimized parameters for {style_name}: {optimized_params}")

        return optimized_params

    def closeEvent(self, event):
        """Ensure the thread stops when closing the app."""
        if self.thread and self.thread.isRunning():
            logging.info("Stopping thread before application close...")
            # Disconnect signals to prevent memory leaks
            try:
                self.thread.error_signal.disconnect()
                self.thread.info_signal.disconnect()
                self.thread.frame_signal.disconnect()
            except (TypeError, RuntimeError):
                # Signals may not be connected or already disconnected
                pass
            
            self.thread.stop()
            # Wait for thread to finish (with timeout)
            if self.thread.isRunning():
                self.thread.wait(3000)  # Wait up to 3 seconds
                if self.thread.isRunning():
                    logging.warning("Thread did not stop within timeout, terminating...")
                    self.thread.terminate()
                    self.thread.wait(1000)  # Wait for termination
            logging.info("Application closed. WebcamThread stopped.")
        event.accept()

# =============================================================================
# 5. Main Function - App Entry Point
# =============================================================================


def main():
    # Ensure OpenCV warnings are suppressed
    try:
        if hasattr(cv2, 'setLogLevel'):
            if hasattr(cv2, 'LOG_LEVEL_ERROR'):
                cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
            elif hasattr(cv2, 'LOG_LEVEL_SILENT'):
                cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
            else:
                # Try numeric value (4 = ERROR level in OpenCV 4.x)
                cv2.setLogLevel(4)
    except (AttributeError, TypeError):
        pass
    
    # Setup logging with rotation
    file_handler = RotatingFileHandler(
        "webcam_app.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))
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
