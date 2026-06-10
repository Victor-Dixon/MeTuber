# 🎥 MeTuber - Real-Time Webcam Effects & Virtual Camera

A professional webcam effects application with real-time video processing capabilities. Transform your webcam into a professional streaming setup with real-time effects, filters, and virtual camera output for OBS, Zoom, Teams, and more.

---

## 📋 Audit Information

**What is Metuber?**  
MeTuber is a desktop application that applies real-time visual effects to webcam video feeds and outputs the processed video to virtual camera devices (OBS Virtual Camera, UnityCapture) for use in streaming, video conferencing, and content creation applications.

**What does "done" look like?**  
- User can select a camera device and apply visual effects in real-time
- Processed video is available as a virtual camera device for other applications
- Settings and parameters persist across sessions
- Application handles errors gracefully and provides clear feedback

**How do I run it locally?**  
See [Quick Start](#-quick-start) section below. Primary entry point: `python webcam_filter_pyqt5.py` (legacy) or `python src/v2_main.py` (V2 modular version).

**Known Limitations:**
- Windows 10/11 is the primary supported platform (Linux/Mac support is experimental via OpenCV)
- Requires OBS Studio for OBS Virtual Camera backend (optional, UnityCapture is alternative)
- Audio captioning features require PyTorch (~1.5GB download) - optional component
- Some effects are computationally intensive and may cause frame drops on lower-end hardware
- Camera access requires Windows privacy settings to allow desktop apps

**What is experimental vs stable:**
- **Stable**: Core video effects, virtual camera output, device detection, parameter controls, settings persistence
- **Experimental**: V2 modular architecture (`src/v2_main.py`), plugin system (`src/plugins/`), AI parameter optimizer, audio captioning features
- **Legacy**: Original monolithic implementation (`webcam_filter_pyqt5.py`) - functional but being phased out

**Current Maturity Level:** Beta / Pre-production  
**Primary Entry Points:** `webcam_filter_pyqt5.py` (stable), `src/v2_main.py` (experimental modular version)

---

## ✨ Key Features

- **Real-Time Video Effects**: Apply professional-grade filters and effects to your webcam feed with minimal latency
- **Virtual Camera Output**: Stream processed video to OBS Virtual Camera or UnityCapture for use in any application
- **Auto Device Detection**: Automatic camera detection with support for DirectShow (Windows), MSMF, and OpenCV backends
- **Intelligent Parameter Optimization**: AI-powered auto-optimization that analyzes frames and adjusts parameters for best results
- **Performance Controls**: Adaptive frame skipping and FPS limiting to maintain smooth performance
- **Multiple Effect Categories**: 
  - 🎭 **Artistic**: Cartoon, anime, sketch, and artistic effects
  - 🎨 **Color Filters**: Brightness, contrast, saturation, and color adjustments
  - ✏️ **Basic Effects**: Blur, sharpen, edge detection, and more
  - 🌊 **Distortions**: Glitch, halftone, and creative distortions
- **Live Preview**: Real-time preview of effects before streaming
- **Snapshot Capture**: Save processed frames as images
- **Settings Persistence**: Automatically saves your preferences and parameters
- **Modular Design**: Easy to add new effects and styles

## 🤖 Twitch Bots

Twitch IRC bot scaffolds (merged from StreamerTools) live under `twitch_bots/`:

```bash
pip install -e .
copy twitch_bots\scaffold\.env.example .env
# Edit .env: TWITCH_BOT_TOKEN, TWITCH_CHANNEL, TWITCH_BOT_NICK

python -m twitch_bots.echo_bot
```

See `twitch_bots/README.md` and `docs/STREAMERTOOLS_MERGE.md` for details.

## 🌐 LAN Web Filter Tester

Test every filter from any device on your WiFi/LAN (no PyQt GUI required):

```bash
pip install -r requirements-core.txt -r requirements-web.txt
python run_web.py
```

The server binds to `0.0.0.0` and prints your LAN URL (e.g. `http://192.168.x.x:8765`). Use the web UI to pick a filter, adjust parameters, run single-filter tests, or batch-test all filters. Errors are surfaced explicitly in test mode.

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Windows 10/11 (primary platform, Linux/Mac support via OpenCV)
- Webcam/camera device
- OBS Studio (optional, for OBS Virtual Camera backend)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd MeTuber
   ```

2. **Set up a Python virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   
   **Option A: Core only (~200MB) - Recommended for most users:**
   ```bash
   pip install -r requirements-core.txt
   ```
   
   **Option B: Full install (~2GB) - Includes audio captioning features:**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Note**: The full install includes PyTorch (~1.5GB) via `openai-whisper` for speech recognition. 
   The core installation is sufficient for video effects and virtual camera features.

4. **Run the application:**
   ```bash
   python webcam_filter_pyqt5.py
   ```

## 📖 Usage Guide

### Starting the Application

1. Launch the application using `python webcam_filter_pyqt5.py`
2. Select your camera device from the dropdown (or use "Auto-detect on start")
3. Choose a style/effect from the categorized tabs
4. Adjust parameters using the sliders and controls
5. Click "Start Virtual Camera" to begin streaming

### Virtual Camera Setup

The application supports two virtual camera backends:

- **OBS Virtual Camera** (default): 
  - Best for Zoom, Teams, Google Meet, Discord
  - Requires OBS Studio to be installed
  - Select "OBS Virtual Camera" in your video conferencing app

- **UnityCapture**:
  - Best for using as a source in OBS Studio
  - Add as "Video Capture Device" in OBS
  - Select "Unity Video Capture" as the device

### Performance Optimization

The application includes several performance features:

- **Adaptive Frame Skipping**: Automatically adjusts frame processing based on system performance
- **FPS Limiting**: Set maximum FPS to reduce CPU/GPU load
- **Manual Frame Skip**: Manually skip frames for lower-end systems
- **Performance Warnings**: Logs warnings when processing is slow (informational only)

### Auto-Optimize Parameters

Click the "Auto Optimize Parameters" button to:
- Analyze the current frame for brightness, contrast, and detail levels
- Automatically adjust style parameters for optimal results
- View detailed optimization results and changes

### Windows Camera Setup

If you encounter camera access issues on Windows:

1. **Enable Camera Access:**
   - Settings → Privacy & Security → Camera
   - Enable "Camera access"
   - Enable "Let apps access your camera"
   - **Enable "Allow desktop apps to access your camera"** (IMPORTANT!)

2. **Close Other Apps:**
   - Close any apps using the camera (Teams, Zoom, Discord, OBS, Chrome, etc.)
   - Check Task Manager for processes using the camera

3. **Try Different USB Ports:**
   - Prefer rear motherboard USB ports
   - Try unplugging and replugging the camera

## 🏗️ Project Structure

```
MeTuber/
├── webcam_filter_pyqt5.py    # Main application entry point
├── webcam_threading.py        # Threading and camera capture logic
├── gui_components/            # Modular GUI components
│   ├── device_selector.py
│   ├── style_tab_manager.py
│   ├── parameter_controls.py
│   └── action_buttons.py
├── styles/                    # Style/effect implementations
│   ├── base.py               # Base Style class
│   ├── artistic/             # Artistic effects (cartoon, sketch, etc.)
│   ├── basic/                # Basic filters
│   ├── color_filters/        # Color adjustments
│   ├── distortions/          # Distortion effects
│   └── effects/              # Special effects
├── src/                      # Additional source code
│   ├── gui/                  # GUI modules
│   ├── plugins/              # Plugin system
│   └── services/             # Service layer
├── tests/                    # Test suite
├── twitch_bots/              # Twitch IRC bots (echo bot + scaffold)
├── Transcripts/              # Stream transcript archives
├── snapshots/                # Saved snapshot images
├── config.json               # Saved settings (auto-generated)
└── requirements.txt          # Python dependencies
```

## 🎨 Effect Categories

### Artistic Effects
- **Cartoon Style Pro**: Advanced cartoon/anime effects with multiple presets
- **Sketch Effects**: Pencil sketch and artistic drawing styles
- **Edge Detection**: Advanced edge detection algorithms

### Color Filters
- **Brightness/Contrast**: Adjust image brightness and contrast
- **Saturation**: Control color intensity
- **Color Grading**: Professional color adjustments

### Basic Effects
- **Blur/Sharpen**: Image blurring and sharpening
- **Original**: Passthrough (no effects)

### Distortions
- **Glitch**: Digital glitch effects
- **Halftone**: Halftone printing effects
- **Creative Distortions**: Various artistic distortions

## 🔧 Configuration

Settings are automatically saved to `config.json`:
- Selected camera device
- Current style and parameters
- Virtual camera backend preference
- Snapshot save directory

## 🐛 Troubleshooting

### "QThread: Destroyed while thread is still running"
- **Fixed!** This issue has been resolved. The application now properly waits for threads to finish before closing.

### Camera Not Detected
- Check Windows Camera privacy settings (see Windows Camera Setup above)
- Ensure no other apps are using the camera
- Try selecting "Auto-detect on start" in the device dropdown
- Check that camera drivers are installed

### Performance Issues
- Reduce Max FPS in Performance Settings
- Increase Frame Skip value
- The adaptive skip mechanism will automatically adjust if needed
- Performance warnings are informational and don't indicate errors

### Virtual Camera Not Working
- For OBS backend: Ensure OBS Studio is installed
- For UnityCapture: Check that UnityCapture driver is installed
- Try restarting the application
- Check that "Send frames to Virtual Camera" checkbox is enabled

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest -n auto --cov=styles tests/

# Run specific test file
pytest tests/test_cartoon.py

# Run with coverage report
pytest --cov=styles --cov-report=html tests/
```

## 📝 Development

### Adding New Styles

1. Create a new file in the appropriate `styles/` subfolder
2. Inherit from `Style` base class in `styles/base.py`
3. Implement the `apply` method:
   ```python
   def apply(self, frame, **params):
       # Process frame
       return processed_frame
   ```
4. Define parameters in the `parameters` list
5. Add unit tests

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Document functions and classes
- Run `black` for formatting: `black .`
- Run `flake8` for linting: `flake8 .`

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 🙏 Acknowledgments

- PyQt5 for the GUI framework
- OpenCV for image processing
- PyAV for camera capture
- pyvirtualcam for virtual camera support
- OBS Studio for virtual camera backend

## 🔄 Recent Updates

- **Thread Safety**: Fixed QThread cleanup issues - threads now properly stop before application exit
- **Performance**: Added adaptive frame skipping for better performance on lower-end systems
- **Auto-Optimization**: Enhanced AI-powered parameter optimization with frame analysis
- **Device Detection**: Improved Windows camera detection with multiple backend support
- **Error Handling**: Better error messages and troubleshooting guidance

---

**Get started and make your streams shine with personalized filters and effects!** 🚀
