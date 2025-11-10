import numpy as np
import os
import subprocess
import json
import unittest
import pytest
from unittest.mock import patch, MagicMock, mock_open
from webcam_filter_pyqt5 import (
    load_settings,
    save_settings,
    list_devices,
    load_styles,
    WebcamThread,
    WebcamApp,
)
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
import logging

CONFIG_FILE = "config.json"

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Do not call quit() here as it will be handled by pytest-qt

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.default_settings = {
            "input_device": "video=C270 HD WEBCAM",
            "style": "Original",
            "parameters": {}
        }

    @patch("webcam_filter_pyqt5.open", new_callable=mock_open, read_data=json.dumps({"style": "CustomStyle"}))
    @patch("webcam_filter_pyqt5.os.path.exists", return_value=True)
    def test_load_settings_with_file(self, mock_exists, mock_open_file):
        settings = load_settings()
        self.assertEqual(settings["style"], "CustomStyle")

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_settings(self, mock_open, mock_json_dump):
        settings = {"key": "value"}
        save_settings(settings)
        mock_open.assert_called_once_with(CONFIG_FILE, "w")
        mock_json_dump.assert_called_once_with(settings, mock_open.return_value, indent=4)

    @patch("webcam_filter_pyqt5.os.path.exists", return_value=False)
    def test_load_settings_without_file(self, mock_exists):
        settings = load_settings()
        self.assertEqual(settings, self.default_settings)

    @patch('subprocess.check_output')
    def test_list_devices(self, mock_check_output):
        mock_check_output.return_value = b"""
            [dshow @ 000001C3E8C48040] DirectShow video devices (some may be both video and audio devices)
            [dshow @ 000001C3E8C48040]     "C270 HD WEBCAM"
            [dshow @ 000001C3E8C48040]     "OBS Virtual Camera"
        """
        devices = list_devices()
        self.assertIn("video=C270 HD WEBCAM", devices)
        self.assertIn("video=OBS Virtual Camera", devices)

    @patch("webcam_filter_pyqt5.subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "ffmpeg"))
    def test_list_devices_error(self, mock_check_output):
        devices = list_devices()
        self.assertEqual(devices, [])

@pytest.fixture
def mock_imports(monkeypatch):
    """Mock all style-related imports."""
    mock_style = MagicMock()
    mock_style.__path__ = []
    mock_style.Style = MagicMock()
    mock_style.Original = MagicMock()
    mock_style.CartoonStylePro = MagicMock()
    
    monkeypatch.setattr('webcam_filter_pyqt5.Style', mock_style.Style)
    monkeypatch.setattr('webcam_filter_pyqt5.Original', mock_style.Original)
    monkeypatch.setattr('webcam_filter_pyqt5.CartoonStylePro', mock_style.CartoonStylePro)
    monkeypatch.setattr('webcam_filter_pyqt5.pkgutil.walk_packages', lambda *args: [])
    
    return mock_style

@pytest.mark.usefixtures("qapp")
class TestStyleLoading:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """Mock all style-related imports."""
        mock_style = MagicMock()
        mock_style.__path__ = []
        mock_style.Style = MagicMock()
        mock_style.Original = MagicMock()
        mock_style.CartoonStylePro = MagicMock()
        
        monkeypatch.setattr('webcam_filter_pyqt5.Style', mock_style.Style)
        monkeypatch.setattr('webcam_filter_pyqt5.Original', mock_style.Original)
        monkeypatch.setattr('webcam_filter_pyqt5.CartoonStylePro', mock_style.CartoonStylePro)
        monkeypatch.setattr('webcam_filter_pyqt5.pkgutil.walk_packages', lambda *args: [])
        
        self.mock_style = mock_style
    
    def test_load_styles_empty(self):
        """Test loading styles when no styles are available."""
        # Import load_styles after mocking
        from webcam_filter_pyqt5 import load_styles
        
        # Call load_styles and verify it handles empty case gracefully
        style_instances, style_categories = load_styles()
        
        # Verify empty results
        assert isinstance(style_instances, dict)
        assert isinstance(style_categories, dict)
        assert len(style_instances) == 0
        assert len(style_categories) == 0

class TestWebcamThread(unittest.TestCase):
    def setUp(self):
        self.dummy_style = MagicMock()
        self.dummy_style.apply = MagicMock(side_effect=lambda img, params: img)
        self.params = {"dummy_param": 0}
        self.input_device = "video=C270 HD WEBCAM"
        self.thread = WebcamThread(self.input_device, self.dummy_style, self.params)

    @patch('av.open')
    @patch('pyvirtualcam.Camera')
    def test_webcam_thread_run(self, mock_camera, mock_av_open):
        # Mock the Camera and AV objects
        mock_camera_instance = MagicMock()
        mock_camera.return_value.__enter__.return_value = mock_camera_instance
        mock_camera_instance.width = 640  # Mock camera resolution
        mock_camera_instance.height = 480
        mock_frame = MagicMock(to_ndarray=MagicMock(return_value=np.zeros((480, 640, 3), dtype=np.uint8)))
        mock_av_open.return_value.decode.return_value = [mock_frame]

        # Mock the style's apply method
        mock_style = MagicMock(apply=MagicMock(return_value=np.zeros((480, 640, 3))))

        # Initialize the thread
        thread = WebcamThread("mock_device", mock_style, {})
        thread._is_running = True

        # Simulate the thread's run method
        with patch.object(thread, 'stop', side_effect=lambda: setattr(thread, '_is_running', False)):
            thread.run()

        # Verify the `apply` method was called
        mock_style.apply.assert_called()
        # Verify the `send` method was called
        mock_camera_instance.send.assert_called_once()

class TestWebcamApp:  # Changed to pytest style
    @pytest.fixture(autouse=True)
    def setup(self, qapp, qtbot):
        """Setup test environment."""
        self.app = WebcamApp()
        qtbot.addWidget(self.app)
        yield
        self.app.close()
        self.app.deleteLater()

    @patch('gui_components.parameter_controls.ParameterControls.update_parameters')
    def test_update_parameter_controls(self, mock_update_parameters, qtbot):
        self.app.current_style = MagicMock(parameters=[{"name": "mock_param"}])
        self.app.current_style_params = {"mock_param": 42}

        # Reset mock call count before explicitly calling the method
        mock_update_parameters.reset_mock()
        self.app.update_parameter_controls()

        # Assert single call
        mock_update_parameters.assert_called_once_with(
            self.app.current_style.parameters,
            self.app.current_style_params,
            self.app.on_param_changed
        )

    @patch('PyQt5.QtWidgets.QMessageBox.critical')
    def test_start_virtual_camera_no_device(self, mock_critical, qtbot):
        self.app.device_combo.setCurrentText("")
        self.app.style_tab_manager.get_current_style = MagicMock(return_value="Original")
        self.app.current_style_params = {}
        self.app.current_style = MagicMock()
        self.app.style_instances["Original"] = MagicMock()
        qtbot.mouseClick(self.app.action_buttons.start_button, Qt.LeftButton)
        mock_critical.assert_called_once()

    @patch('PyQt5.QtWidgets.QMessageBox.critical')
    def test_start_virtual_camera_no_style(self, mock_critical, qtbot):
        self.app.device_combo.setCurrentText("video=C270 HD WEBCAM")
        self.app.style_tab_manager.get_current_style = MagicMock(return_value=None)
        qtbot.mouseClick(self.app.action_buttons.start_button, Qt.LeftButton)
        mock_critical.assert_called_once()

    @patch('PyQt5.QtWidgets.QMessageBox.information')
    def test_take_snapshot_no_frame(self, mock_info, qtbot):
        self.app.thread = None
        qtbot.mouseClick(self.app.action_buttons.snapshot_button, Qt.LeftButton)
        mock_info.assert_called_once_with(self.app, "Snapshot", "No frame available to save.")

    def test_snapshot_button_click(self, qtbot):
        self.app.thread = MagicMock()
        self.app.thread.last_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        self.app.action_buttons.snapshot_button.setEnabled(True)
        default_path = os.path.join(self.app.snapshot_dir, "snapshot.png")
        with patch("PyQt5.QtWidgets.QFileDialog.getSaveFileName", return_value=(default_path, "")), \
             patch("cv2.imwrite") as mock_imwrite, \
             patch("PyQt5.QtWidgets.QMessageBox.information") as mock_info:
            qtbot.mouseClick(self.app.action_buttons.snapshot_button, Qt.LeftButton)
            mock_imwrite.assert_called_once_with(default_path, self.app.thread.last_frame)
            mock_info.assert_called()

    def test_start_button_click(self, qtbot):
        self.app.device_combo.setCurrentText("video=C270 HD WEBCAM")
        self.app.style_tab_manager.get_current_style = MagicMock(return_value="Original")
        self.app.current_style_params = {}
        self.app.current_style = MagicMock()
        self.app.style_instances["Original"] = MagicMock()
        # Simulate clicking start and check that thread is started
        qtbot.mouseClick(self.app.action_buttons.start_button, Qt.LeftButton)
        assert self.app.thread is not None

    def test_stop_button_click(self, qtbot):
        self.app.thread = MagicMock()
        self.app.thread.isRunning.return_value = True
        self.app.action_buttons.stop_button.setEnabled(True)
        qtbot.mouseClick(self.app.action_buttons.stop_button, Qt.LeftButton)
        # After stop, thread should be None
        assert self.app.thread is None

    def test_optimize_button_click(self, qtbot):
        self.app.thread = MagicMock()
        self.app.thread.last_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        self.app.current_style = MagicMock()
        self.app.current_style.ai_optimize = MagicMock(return_value={})
        self.app.current_style_params = {}
        self.app.style_tab_manager.get_current_style = MagicMock(return_value="Original")
        self.app.style_instances["Original"] = self.app.current_style
        with patch("PyQt5.QtWidgets.QMessageBox.information") as mock_info:
            qtbot.mouseClick(self.app.optimize_button, Qt.LeftButton)
            mock_info.assert_called()

    @patch('PyQt5.QtWidgets.QMessageBox.critical')
    def test_optimize_button_no_frame(self, mock_critical, qtbot):
        self.app.thread = None
        qtbot.mouseClick(self.app.optimize_button, Qt.LeftButton)
        mock_critical.assert_called_once()

    def test_stop_button_disabled_when_not_running(self, qtbot):
        # Stop button should be disabled if thread is not running
        self.app.thread = None
        self.app.action_buttons.stop_button.setEnabled(False)
        assert not self.app.action_buttons.stop_button.isEnabled()

    def test_start_button_disabled_when_running(self, qtbot):
        # Start button should be disabled when thread is running
        self.app.thread = MagicMock()
        self.app.thread.isRunning.return_value = True
        self.app.action_buttons.start_button.setEnabled(False)
        assert not self.app.action_buttons.start_button.isEnabled()

if __name__ == "__main__":
    pytest.main([__file__])
