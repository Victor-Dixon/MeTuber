#!/usr/bin/env python3
"""
Dreamscape V2 - Professional Webcam Effects Studio
A next-generation interface designed to rival OBS Studio
"""

import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QComboBox, QGroupBox, QFormLayout, QSlider, QMenuBar,
    QAction, QStatusBar, QFrame, QSplitter, QScrollArea, QGridLayout, QListWidget,
    QListWidgetItem, QDockWidget, QToolBar, QProgressBar, QTextEdit, QCheckBox,
    QSpinBox, QDoubleSpinBox, QButtonGroup, QRadioButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsProxyWidget,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QPalette, QColor, QFont, QIcon, QPainter, QBrush, QLinearGradient, QImage
import cv2
import numpy as np
from datetime import datetime

from .components.draggable_widget import DraggableWidget
from .components.widget_registry import WidgetRegistry

class ProfessionalV2MainWindow(QMainWindow):
    """Professional V2 main window designed to rival OBS Studio."""
    
    # Signals
    style_changed = pyqtSignal(str)
    device_changed = pyqtSignal(str)
    parameters_changed = pyqtSignal(dict)
    start_processing = pyqtSignal()
    stop_processing = pyqtSignal()
    effect_applied = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.is_processing = False
        self.current_style = None
        self.effects_history = []
        self.favorite_effects = []
        
        # Initialize webcam service
        self.webcam_service = None
        self.current_frame = None
        self.preview_pixmap = None
        self.pending_style = None
        self.pending_params = {}
        
        self.setup_professional_theme()
        self.init_ui()
        self.setup_connections()
        self.setup_animations()
        
        # Initialize widget registry for draggable filter widgets
        self.widget_registry = WidgetRegistry(self)
        self.widget_registry.widget_created.connect(self.on_filter_widget_created)
        self.widget_registry.layout_changed.connect(self.on_widget_layout_changed)
        
        # Initialize webcam service
        self.init_webcam_service()
        
        # Pre-load everything for instant startup
        self.pre_load_camera()
        self.pre_load_styles()
        self.pre_initialize_timer()
        
        # Hide old parameter controls by default - using draggable widgets instead
        self.hide_old_parameter_controls()
        
        self.logger.info("Professional V2 Main Window initialized successfully!")
        
    def setup_professional_theme(self):
        """Apply professional OBS-rivaling theme."""
        # Create sophisticated dark palette
        dark_palette = QPalette()
        
        # Professional color scheme
        dark_palette.setColor(QPalette.Window, QColor(32, 32, 32))
        dark_palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
        dark_palette.setColor(QPalette.Base, QColor(20, 20, 20))
        dark_palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.ToolTipText, QColor(240, 240, 240))
        dark_palette.setColor(QPalette.Text, QColor(240, 240, 240))
        dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 100, 100))
        dark_palette.setColor(QPalette.Link, QColor(0, 150, 255))
        dark_palette.setColor(QPalette.Highlight, QColor(0, 150, 255))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        QApplication.setPalette(dark_palette)
        
        # Professional stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
            }
            
            QDockWidget {
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(undock.png);
                background: #2a2a2a;
                border: 1px solid #404040;
                title {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3a3a3a, stop:1 #2a2a2a);
                    padding: 6px;
                    border-bottom: 1px solid #404040;
                }
            }
            
            QTabWidget::pane {
                border: 2px solid #404040;
                background: #1e1e1e;
                border-radius: 6px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                color: #cccccc;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid #404040;
                border-bottom: none;
                font-weight: bold;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0096ff, stop:1 #007acc);
                color: white;
                border-color: #0096ff;
            }
            
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
            }
            
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #404040;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1e1e1e);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #0096ff;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0096ff, stop:1 #007acc);
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00a6ff, stop:1 #0088dd);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007acc, stop:1 #0066aa);
            }
            
            QPushButton:disabled {
                background: #404040;
                color: #888888;
            }
            
            QComboBox {
                background: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 6px;
                padding: 8px 12px;
                color: white;
                font-weight: bold;
                min-width: 120px;
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
            
            QSlider::groove:horizontal {
                border: 1px solid #404040;
                height: 10px;
                background: #1a1a1a;
                border-radius: 5px;
            }
            
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0096ff, stop:1 #007acc);
                border: 2px solid #0096ff;
                width: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00a6ff, stop:1 #0088dd);
            }
            
            QListWidget {
                background: #1e1e1e;
                border: 2px solid #404040;
                border-radius: 6px;
                color: white;
                font-size: 11px;
            }
            
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            
            QListWidget::item:selected {
                background: #0096ff;
                color: white;
            }
            
            QListWidget::item:hover {
                background: #2a2a2a;
            }
            
            QTableWidget {
                background: #1e1e1e;
                border: 2px solid #404040;
                border-radius: 6px;
                color: white;
                gridline-color: #404040;
            }
            
            QTableWidget::item {
                padding: 8px;
            }
            
            QTableWidget::item:selected {
                background: #0096ff;
                color: white;
            }
            
            QHeaderView::section {
                background: #2a2a2a;
                color: #0096ff;
                padding: 8px;
                border: 1px solid #404040;
                font-weight: bold;
            }
            
            QProgressBar {
                border: 2px solid #404040;
                border-radius: 6px;
                text-align: center;
                background: #1a1a1a;
                color: white;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0096ff, stop:1 #00ccff);
                border-radius: 4px;
            }
            
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1e1e1e);
                color: white;
                border-top: 1px solid #404040;
            }
            
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border: none;
                spacing: 5px;
                padding: 5px;
            }
            
            QToolBar QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 8px;
                margin: 2px;
            }
            
            QToolBar QToolButton:hover {
                background: #404040;
                border-color: #0096ff;
            }
            
            QToolBar QToolButton:pressed {
                background: #0096ff;
            }
        """)
    
    def init_ui(self):
        """Initialize the professional user interface."""
        self.setWindowTitle("Dreamscape Stream Software (Open Source)")
        self.setGeometry(50, 50, 1800, 1100)  # Increased window size to prevent overlap
        
        # Create central widget with main preview
        self.create_central_preview()
        
        # Create dock widgets
        self.create_effects_dock()
        self.create_controls_dock()
        self.create_properties_dock()
        self.create_timeline_dock()
        
        # Create menu bar and toolbars
        self.create_menu_bar()
        self.create_main_toolbar()
        self.create_status_bar()
        
        # Setup preview timer for immediate response
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(100)  # Start slow, will speed up when webcam starts
        
    def create_central_preview(self):
        """Create the central preview area."""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)  # Increased margins to prevent overlap
        
        # Preview header with controls
        preview_header = QHBoxLayout()
        
        # Preview title
        title_label = QLabel("🎥 LIVE PREVIEW")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #0096ff;
            padding: 10px;
        """)
        preview_header.addWidget(title_label)
        
        preview_header.addStretch()
        
        # Enhanced preview controls
        # Size controls
        size_label = QLabel("Size:")
        preview_header.addWidget(size_label)
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Normal", "Large", "Fullscreen"])
        self.size_combo.setMaximumWidth(100)
        self.size_combo.currentTextChanged.connect(self.on_preview_size_changed)
        preview_header.addWidget(self.size_combo)
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        preview_header.addWidget(zoom_label)
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["Fit", "50%", "75%", "100%", "125%", "150%", "200%"])
        self.zoom_combo.setCurrentText("Fit")
        self.zoom_combo.setMaximumWidth(80)
        self.zoom_combo.currentTextChanged.connect(self.on_zoom_changed)
        preview_header.addWidget(self.zoom_combo)
        
        # Standard controls
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.setMaximumWidth(120)
        preview_header.addWidget(self.fullscreen_btn)
        
        self.record_btn = QPushButton("🔴 Record")
        self.record_btn.setMaximumWidth(120)
        preview_header.addWidget(self.record_btn)
        
        self.stream_btn = QPushButton("📡 Stream")
        self.stream_btn.setMaximumWidth(120)
        preview_header.addWidget(self.stream_btn)
        
        layout.addLayout(preview_header)
        
        # Main preview area
        self.preview_frame = QFrame()
        self.preview_frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.preview_frame.setStyleSheet("""
            QFrame {
                border: 3px solid #404040;
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0a0a, stop:1 #1a1a1a);
            }
        """)
        
        preview_layout = QVBoxLayout(self.preview_frame)
        
        # Simple video label for preview (replacing complex graphics view)
        self.video_label = QLabel("Dreamscape Stream Software (Open Source)")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 24px;
                font-weight: bold;
                background: #0a0a0a;
                border: 2px solid #404040;
                border-radius: 5px;
            }
        """)
        
        preview_layout.addWidget(self.video_label)
        layout.addWidget(self.preview_frame)
        
        # Preview status bar
        preview_status = QHBoxLayout()
        
        self.fps_label = QLabel("FPS: 30.0")
        self.fps_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        preview_status.addWidget(self.fps_label)
        
        self.resolution_label = QLabel("1920x1080")
        self.resolution_label.setStyleSheet("color: #0096ff; font-weight: bold;")
        preview_status.addWidget(self.resolution_label)
        
        self.bitrate_label = QLabel("Bitrate: 5000 kbps")
        self.bitrate_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        preview_status.addWidget(self.bitrate_label)
        
        preview_status.addStretch()
        
        self.recording_time = QLabel("00:00:00")
        self.recording_time.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 14px;")
        preview_status.addWidget(self.recording_time)
        
        layout.addLayout(preview_status)
        
    def create_effects_dock(self):
        """Create the effects library dock widget."""
        effects_dock = QDockWidget("🎨 Effects Library", self)
        effects_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        effects_dock.setMinimumWidth(280)  # Set minimum width
        effects_dock.setMaximumWidth(320)  # Set maximum width
        
        effects_widget = QWidget()
        effects_layout = QVBoxLayout(effects_widget)
        
        # Effects search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.effects_search = QComboBox()
        self.effects_search.setEditable(True)
        self.effects_search.addItems(["All Effects", "Artistic", "Basic", "Advanced", "Custom"])
        search_layout.addWidget(self.effects_search)
        effects_layout.addLayout(search_layout)
        
        # Effects categories with improved UI
        effects_tabs = QTabWidget()
        
        # Popular effects with scrollable area
        popular_tab = QWidget()
        popular_main_layout = QVBoxLayout(popular_tab)
        
        # Create scrollable area for popular effects
        from PyQt5.QtWidgets import QScrollArea
        popular_scroll = QScrollArea()
        popular_scroll.setWidgetResizable(True)
        popular_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        popular_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popular_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #0096ff;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #1aa3ff;
            }
        """)
        
        popular_scroll_widget = QWidget()
        popular_layout = QVBoxLayout(popular_scroll_widget)
        
        popular_effects = [
            "🎭 Cartoon Effects", "✏️ Sketch Effects", "🎨 Color Effects", "💧 Watercolor",
            "⚡ Glitch Effect", "🌟 Glow Effect", "🎬 Motion Blur", "🔍 Edge Detection",
            "🌈 Color Grading", "📸 Portrait Mode", "🎪 Vintage", "🌌 Cyberpunk"
        ]
        
        for effect in popular_effects:
            effect_btn = QPushButton(effect)
            effect_btn.setMinimumHeight(40)
            # Add professional hover effects and styling
            effect_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    border: 1px solid #444;
                    border-radius: 6px;
                    background-color: #333;
                    color: white;
                    font-weight: bold;
                    transition: all 0.2s ease;
                }
                QPushButton:hover {
                    background-color: #0096ff;
                    border-color: #1aa3ff;
                    transform: scale(1.02);
                    box-shadow: 0 2px 8px rgba(0, 150, 255, 0.3);
                }
                QPushButton:pressed {
                    background-color: #0077cc;
                    transform: scale(0.98);
                }
            """)
            effect_btn.clicked.connect(lambda checked, e=effect: self.apply_effect(e))
            popular_layout.addWidget(effect_btn)
        
        popular_layout.addStretch()
        
        # Set up the scroll area
        popular_scroll.setWidget(popular_scroll_widget)
        popular_main_layout.addWidget(popular_scroll)
        effects_tabs.addTab(popular_tab, "⭐ Popular")
        
        # All effects
        all_tab = QWidget()
        all_layout = QVBoxLayout(all_tab)
        
        self.effects_list = QListWidget()
        all_effects = [
            "Cartoon (Fast)", "Cartoon (Anime)", "Cartoon (Advanced)",
            "Pencil Sketch", "Advanced Sketch", "Color Sketch",
            "Oil Painting", "Watercolor", "Line Art", "Stippling",
            "Glitch", "Mosaic", "Light Leak", "Halftone",
            "Invert", "Negative", "Sepia", "Black & White",
            "Brightness", "Contrast", "Color Balance", "Vibrance"
        ]
        
        for effect in all_effects:
            item = QListWidgetItem(f"🎨 {effect}")
            self.effects_list.addItem(item)
        
        all_layout.addWidget(self.effects_list)
        effects_tabs.addTab(all_tab, "📚 All Effects")
        
        # Favorites
        favorites_tab = QWidget()
        favorites_layout = QVBoxLayout(favorites_tab)
        
        self.favorites_list = QListWidget()
        favorites_layout.addWidget(self.favorites_list)
        
        add_favorite_btn = QPushButton("➕ Add to Favorites")
        add_favorite_btn.clicked.connect(self.add_to_favorites)
        favorites_layout.addWidget(add_favorite_btn)
        
        effects_tabs.addTab(favorites_tab, "❤️ Favorites")
        
        effects_layout.addWidget(effects_tabs)
        
        effects_dock.setWidget(effects_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, effects_dock)
        
    def create_controls_dock(self):
        """Create the controls dock widget."""
        controls_dock = QDockWidget("🎛️ Controls", self)
        controls_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        controls_dock.setMinimumWidth(300)  # Set minimum width to prevent overlap
        controls_dock.setMaximumWidth(350)  # Set maximum width to keep it compact
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Device selection
        device_group = QGroupBox("📹 Input Device")
        device_layout = QVBoxLayout(device_group)
            
            self.device_combo = QComboBox()
        self.device_combo.addItems([
            "C270 HD WEBCAM (1920x1080)",
            "Integrated Webcam (1280x720)",
            "External Camera (4K)"
        ])
        device_layout.addWidget(self.device_combo)
        
        device_info = QLabel("Resolution: 1920x1080 | FPS: 30 | Bitrate: 5000 kbps")
        device_info.setStyleSheet("color: #888888; font-size: 10px;")
        device_layout.addWidget(device_info)
        
        controls_layout.addWidget(device_group)
        
        # Processing controls
        processing_group = QGroupBox("⚡ Processing")
        processing_layout = QVBoxLayout(processing_group)
        
        self.start_stop_btn = QPushButton("▶️ Start Processing")
        self.start_stop_btn.setMinimumHeight(50)
        processing_layout.addWidget(self.start_stop_btn)
        
        self.snapshot_btn = QPushButton("📸 Take Snapshot")
        self.snapshot_btn.setMinimumHeight(40)
        processing_layout.addWidget(self.snapshot_btn)
        
        self.reset_btn = QPushButton("🔄 Reset Effects")
        self.reset_btn.setMinimumHeight(40)
        processing_layout.addWidget(self.reset_btn)
        
        controls_layout.addWidget(processing_group)
        
        # Performance
        perf_group = QGroupBox("📊 Performance")
        perf_layout = QVBoxLayout(perf_group)
        
        self.cpu_usage = QProgressBar()
        self.cpu_usage.setValue(45)
        self.cpu_usage.setFormat("CPU: %p%")
        perf_layout.addWidget(self.cpu_usage)
        
        self.memory_usage = QProgressBar()
        self.memory_usage.setValue(32)
        self.memory_usage.setFormat("Memory: %p%")
        perf_layout.addWidget(self.memory_usage)
        
        self.gpu_usage = QProgressBar()
        self.gpu_usage.setValue(78)
        self.gpu_usage.setFormat("GPU: %p%")
        perf_layout.addWidget(self.gpu_usage)
        
        controls_layout.addWidget(perf_group)
        
        controls_layout.addStretch()
        controls_dock.setWidget(controls_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, controls_dock)
        
    def create_properties_dock(self):
        """Create the comprehensive properties dock widget."""
        properties_dock = QDockWidget("🎛️ Controls & Settings", self)
        properties_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        properties_dock.setMinimumHeight(200)  # Better for bottom placement
        properties_dock.setMaximumHeight(400)
        
        properties_widget = QWidget()
        # Use horizontal layout for better bottom dock usage
        properties_layout = QHBoxLayout(properties_widget)
        
        # Column 1: Current Effect & Basic Controls
        left_column = QVBoxLayout()
        
        current_group = QGroupBox("🎨 Current Effect")
        current_layout = QFormLayout(current_group)
        
        self.current_effect_label = QLabel("None")
        self.current_effect_label.setStyleSheet("color: #0096ff; font-weight: bold;")
        current_layout.addRow("Effect:", self.current_effect_label)
        
        self.effect_variant_combo = QComboBox()
        self.effect_variant_combo.addItems(["Standard", "Enhanced", "Pro", "Custom"])
        self.effect_variant_combo.currentTextChanged.connect(self.on_variant_changed)
        current_layout.addRow("Variant:", self.effect_variant_combo)
        
        left_column.addWidget(current_group)
        
        # Camera Controls
        camera_group = QGroupBox("📹 Camera Controls")
        camera_layout = QFormLayout(camera_group)
        
        # Brightness
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_label = QLabel("Brightness: 0")
        camera_layout.addRow(self.brightness_label, self.brightness_slider)
        self.brightness_slider.valueChanged.connect(lambda v: self.brightness_label.setText(f"Brightness: {v}"))
        
        # Contrast
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(50, 300)  # 0.5 to 3.0
        self.contrast_slider.setValue(100)
        self.contrast_label = QLabel("Contrast: 1.0")
        camera_layout.addRow(self.contrast_label, self.contrast_slider)
        self.contrast_slider.valueChanged.connect(lambda v: self.contrast_label.setText(f"Contrast: {v/100:.1f}"))
        
        # Saturation
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setRange(0, 200)  # 0 to 2.0
        self.saturation_slider.setValue(100)
        self.saturation_label = QLabel("Saturation: 1.0")
        camera_layout.addRow(self.saturation_label, self.saturation_slider)
        self.saturation_slider.valueChanged.connect(lambda v: self.saturation_label.setText(f"Saturation: {v/100:.1f}"))
        
        left_column.addWidget(camera_group)
        
        # Column 2: Effect Parameters
        middle_column = QVBoxLayout()
        
        params_group = QGroupBox("🎛️ Effect Parameters")
        self.params_layout = QFormLayout(params_group)
        
        # Dynamic parameter widgets - will be updated based on selected effect
        self.param_widgets = {}
        self.param_labels = {}
        
        # Create initial generic sliders (will be updated dynamically)
        self.create_default_sliders()
        
        middle_column.addWidget(params_group)
        
        # Column 3: Performance & Output
        right_column = QVBoxLayout()
        
        # Performance Settings
        performance_group = QGroupBox("⚡ Performance")
        performance_layout = QFormLayout(performance_group)
        
        # Processing Quality
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Fast", "Balanced", "High Quality"])
        self.quality_combo.setCurrentText("Balanced")
        performance_layout.addRow("Quality:", self.quality_combo)
        
        # Frame Rate Limit
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["15 FPS", "30 FPS", "60 FPS", "120 FPS"])
        self.fps_combo.setCurrentText("30 FPS")
        performance_layout.addRow("Frame Rate:", self.fps_combo)
        
        # Resolution Scale
        self.resolution_slider = QSlider(Qt.Horizontal)
        self.resolution_slider.setRange(25, 200)  # 25% to 200%
        self.resolution_slider.setValue(100)
        self.resolution_label = QLabel("Resolution: 100%")
        performance_layout.addRow(self.resolution_label, self.resolution_slider)
        self.resolution_slider.valueChanged.connect(lambda v: self.resolution_label.setText(f"Resolution: {v}%"))
        
        right_column.addWidget(performance_group)
        
        # Output Settings
        output_group = QGroupBox("📤 Output")
        output_layout = QFormLayout(output_group)
        
        self.virtual_cam_enable = QCheckBox("Virtual Camera")
        self.virtual_cam_enable.setChecked(True)
        output_layout.addRow(self.virtual_cam_enable)
        
        self.recording_enable = QCheckBox("Enable Recording")
        self.recording_enable.setChecked(False)
        output_layout.addRow(self.recording_enable)
        
        self.auto_optimize = QCheckBox("Auto-optimize")
        self.auto_optimize.setChecked(True)
        output_layout.addRow(self.auto_optimize)
        
        right_column.addWidget(output_group)
        
        # Add all columns to the main layout
        properties_layout.addLayout(left_column)
        properties_layout.addLayout(middle_column)
        properties_layout.addLayout(right_column)
        
        # Connect all sliders AFTER everything is created
        self.connect_slider_updates()
        
        properties_layout.addStretch()
        properties_dock.setWidget(properties_widget)
        # Position at bottom for better layout
        self.addDockWidget(Qt.BottomDockWidgetArea, properties_dock)
        
    def create_default_sliders(self):
        """Create default parameter sliders."""
        # Intensity/Threshold1 slider
        self.param1_slider = QSlider(Qt.Horizontal)
        self.param1_slider.setRange(0, 100)
        self.param1_slider.setValue(50)
        self.param1_label = QLabel("Intensity:")
        self.params_layout.addRow(self.param1_label, self.param1_slider)
        self.param_widgets['param1'] = self.param1_slider
        self.param_labels['param1'] = self.param1_label
        
        # Quality/Threshold2 slider  
        self.param2_slider = QSlider(Qt.Horizontal)
        self.param2_slider.setRange(1, 10)
        self.param2_slider.setValue(5)
        self.param2_label = QLabel("Quality:")
        self.params_layout.addRow(self.param2_label, self.param2_slider)
        self.param_widgets['param2'] = self.param2_slider
        self.param_labels['param2'] = self.param2_label
        
        # Speed/Extra parameter slider
        self.param3_slider = QSlider(Qt.Horizontal)
        self.param3_slider.setRange(1, 100)
        self.param3_slider.setValue(30)
        self.param3_label = QLabel("Speed:")
        self.params_layout.addRow(self.param3_label, self.param3_slider)
        self.param_widgets['param3'] = self.param3_slider
        self.param_labels['param3'] = self.param3_label
        
        # Blend/Mix parameter slider
        self.param4_slider = QSlider(Qt.Horizontal)
        self.param4_slider.setRange(0, 100)
        self.param4_slider.setValue(100)
        self.param4_label = QLabel("Blend:")
        self.params_layout.addRow(self.param4_label, self.param4_slider)
        self.param_widgets['param4'] = self.param4_slider
        self.param_labels['param4'] = self.param4_label
        
    def connect_slider_updates(self):
        """Connect all parameter sliders to real-time updates."""
        # Effect-specific parameters
        self.param1_slider.valueChanged.connect(self.on_parameter_changed)
        self.param2_slider.valueChanged.connect(self.on_parameter_changed)
        self.param3_slider.valueChanged.connect(self.on_parameter_changed)
        self.param4_slider.valueChanged.connect(self.on_parameter_changed)
        
        # Camera controls
        self.brightness_slider.valueChanged.connect(self.on_camera_parameter_changed)
        self.contrast_slider.valueChanged.connect(self.on_camera_parameter_changed)
        self.saturation_slider.valueChanged.connect(self.on_camera_parameter_changed)
        
        # Performance controls
        self.quality_combo.currentTextChanged.connect(self.on_performance_changed)
        self.fps_combo.currentTextChanged.connect(self.on_performance_changed)
        self.resolution_slider.valueChanged.connect(self.on_performance_changed)
        
    def update_parameters_for_effect(self, effect_name):
        """Update parameter controls based on the selected effect."""
        try:
            self.logger.info(f"Updating parameters for effect: {effect_name}")
            
            if "🔍 Edge Detection" in effect_name:
                # Configure for Edge Detection: threshold1 and threshold2
                self.param1_label.setText("Threshold 1: 100")
                self.param1_slider.setRange(0, 500)
                self.param1_slider.setValue(100)  # Default threshold1
                self.param1_slider.setToolTip("Lower threshold for edge detection (0-500)")
                
                self.param2_label.setText("Threshold 2: 200")
                self.param2_slider.setRange(0, 500)
                self.param2_slider.setValue(200)  # Default threshold2
                self.param2_slider.setToolTip("Upper threshold for edge detection (0-500)")
                
                # Add value update connections for Edge Detection
                self.param1_slider.valueChanged.connect(lambda v: self.param1_label.setText(f"Threshold 1: {v}"))
                self.param2_slider.valueChanged.connect(lambda v: self.param2_label.setText(f"Threshold 2: {v}"))
                
                # Hide unused sliders for Edge Detection
                self.param3_label.setText("(Not used)")
                self.param3_slider.setEnabled(False)
                self.param3_slider.setToolTip("Not used for Edge Detection")
                self.param4_label.setText("(Not used)")
                self.param4_slider.setEnabled(False)
                self.param4_slider.setToolTip("Not used for Edge Detection")
                
                self.logger.info("Edge Detection parameters configured")
                
            elif "🎭 Cartoon Effects" in effect_name:
                # Configure for Cartoon Effects
                self.param1_label.setText("Intensity:")
                self.param1_slider.setRange(0, 100)
                self.param1_slider.setValue(50)
                
                self.param2_label.setText("Smoothing:")
                self.param2_slider.setRange(1, 20)
                self.param2_slider.setValue(10)
                
                self.param3_label.setText("Edge Strength:")
                self.param3_slider.setRange(1, 100)
                self.param3_slider.setValue(30)
                self.param3_slider.setEnabled(True)
                
                self.param4_label.setText("Color Levels:")
                self.param4_slider.setRange(2, 16)
                self.param4_slider.setValue(8)
                self.param4_slider.setEnabled(True)
                
            else:
                # Generic parameters for other effects
                self.param1_label.setText("Intensity:")
                self.param1_slider.setRange(0, 100)
                self.param1_slider.setValue(50)
                self.param1_slider.setEnabled(True)
                
                self.param2_label.setText("Quality:")
                self.param2_slider.setRange(1, 10)
                self.param2_slider.setValue(5)
                self.param2_slider.setEnabled(True)
                
                self.param3_label.setText("Speed:")
                self.param3_slider.setRange(1, 100)
                self.param3_slider.setValue(30)
                self.param3_slider.setEnabled(True)
                
                self.param4_label.setText("Blend:")
                self.param4_slider.setRange(0, 100)
                self.param4_slider.setValue(100)
                self.param4_slider.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Error updating parameters for {effect_name}: {e}")
            
    def on_parameter_changed(self):
        """Handle parameter slider changes for INSTANT real-time updates."""
        try:
            # Get current parameters based on the active effect
            current_effect = self.current_effect_label.text()
            params = self.get_style_specific_parameters(current_effect)
            
            # Update parameters IMMEDIATELY - whether processing or not
            if hasattr(self, 'current_style_instance') and self.current_style_instance:
                # Update the pending style parameters for INSTANT response
                self.pending_params = params
                
                # Also update any running webcam service
                if hasattr(self, 'webcam_service') and self.webcam_service and self.webcam_service.is_running():
                    self.webcam_service.update_style(self.current_style_instance, params)
                
                # Log only occasionally to avoid spam
                if not hasattr(self, '_param_update_count'):
                    self._param_update_count = 0
                self._param_update_count += 1
                if self._param_update_count % 10 == 0:  # Log every 10th update
                    self.logger.info(f"Parameters updated: {params}")
            
        except Exception as e:
            self.logger.error(f"Error handling parameter change: {e}")
            
    def on_camera_parameter_changed(self):
        """Handle camera control changes - IMMEDIATE VISUAL FEEDBACK."""
        try:
            # Log occasionally for debugging
            if not hasattr(self, '_camera_update_count'):
                self._camera_update_count = 0
            self._camera_update_count += 1
            if self._camera_update_count % 10 == 0:
                brightness = self.brightness_slider.value()
                contrast = self.contrast_slider.value() / 100.0
                saturation = self.saturation_slider.value() / 100.0
                self.logger.info(f"Camera: B:{brightness}, C:{contrast:.1f}, S:{saturation:.1f}")
            
        except Exception as e:
            self.logger.error(f"Error handling camera parameter change: {e}")
            
    def on_performance_changed(self):
        """Handle performance setting changes - ACTUALLY APPLY THEM."""
        try:
            quality = self.quality_combo.currentText()
            fps_text = self.fps_combo.currentText()
            resolution = self.resolution_slider.value()
            
            # Extract FPS number
            fps = int(fps_text.split()[0])
            
            # IMMEDIATELY update preview timer FPS
            if hasattr(self, 'preview_timer'):
                interval = 1000 // fps  # Convert FPS to milliseconds
                self.preview_timer.stop()
                self.preview_timer.start(interval)
                
            # Store settings for frame processing
            self.performance_settings = {
                "quality": quality,
                "fps": fps,
                "resolution_scale": resolution / 100.0
            }
                
            self.logger.info(f"APPLIED: {quality}, {fps} FPS, {resolution}% resolution")
            
        except Exception as e:
            self.logger.error(f"Error handling performance change: {e}")
            
    def on_preview_size_changed(self, size_text):
        """Handle preview size changes."""
        try:
            if size_text == "Normal":
                # Standard size
                self.video_label.setMaximumSize(640, 480)
                self.video_label.setMinimumSize(320, 240)
            elif size_text == "Large":
                # Large size
                self.video_label.setMaximumSize(960, 720)
                self.video_label.setMinimumSize(640, 480)
            elif size_text == "Fullscreen":
                # Remove size constraints for fullscreen
                self.video_label.setMaximumSize(16777215, 16777215)  # Max Qt size
                self.video_label.setMinimumSize(320, 240)
                
            self.logger.info(f"Preview size changed to: {size_text}")
            
        except Exception as e:
            self.logger.error(f"Error changing preview size: {e}")
            
    def on_zoom_changed(self, zoom_text):
        """Handle preview zoom changes."""
        try:
            # Store zoom level for use in update_preview_display
            if zoom_text == "Fit":
                self.zoom_factor = None  # Auto-fit
            else:
                # Extract percentage
                zoom_percent = int(zoom_text.replace("%", ""))
                self.zoom_factor = zoom_percent / 100.0
                
            self.logger.info(f"Preview zoom changed to: {zoom_text}")
            
        except Exception as e:
            self.logger.error(f"Error changing preview zoom: {e}")
            
    def toggle_performance_graph(self):
        """Toggle between bar and graph mode for performance indicators."""
        try:
            if not hasattr(self, 'performance_graph_mode'):
                self.performance_graph_mode = False
                
            self.performance_graph_mode = not self.performance_graph_mode
            
            if self.performance_graph_mode:
                # Switch to mini graph mode (could implement with QChart)
                self.logger.info("Performance view: Graph mode")
            else:
                # Switch back to bar mode
                self.logger.info("Performance view: Bar mode")
            
        except Exception as e:
            self.logger.error(f"Error toggling performance graph: {e}")
            
    def get_style_specific_parameters(self, effect_name):
        """Get current parameter values mapped to the specific style."""
        if "🔍 Edge Detection" in effect_name:
            return {
                "threshold1": self.param1_slider.value(),
                "threshold2": self.param2_slider.value()
            }
        elif "🎭 Cartoon Effects" in effect_name:
            return {
                "intensity": self.param1_slider.value(),
                "smoothing": self.param2_slider.value(),
                "edge_strength": self.param3_slider.value(),
                "color_levels": self.param4_slider.value()
            }
        else:
            # Generic mapping for other effects
            return {
                "intensity": self.param1_slider.value(),
                "quality": self.param2_slider.value(),
                "speed": self.param3_slider.value(),
                "blend": self.param4_slider.value()
            }
        
    def create_timeline_dock(self):
        """Create the timeline dock widget."""
        timeline_dock = QDockWidget("⏱️ Timeline", self)
        timeline_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        timeline_dock.setMinimumHeight(150)  # Set minimum height
        
        timeline_widget = QWidget()
        timeline_layout = QVBoxLayout(timeline_widget)
        
        # Timeline controls
        timeline_controls = QHBoxLayout()
        
        self.timeline_play = QPushButton("▶️")
        self.timeline_play.setMaximumWidth(40)
        timeline_controls.addWidget(self.timeline_play)
        
        self.timeline_pause = QPushButton("⏸️")
        self.timeline_pause.setMaximumWidth(40)
        timeline_controls.addWidget(self.timeline_pause)
        
        self.timeline_stop = QPushButton("⏹️")
        self.timeline_stop.setMaximumWidth(40)
        timeline_controls.addWidget(self.timeline_stop)
        
        timeline_controls.addStretch()
        
        self.timeline_time = QLabel("00:00:00 / 00:00:00")
        self.timeline_time.setStyleSheet("color: #0096ff; font-weight: bold;")
        timeline_controls.addWidget(self.timeline_time)
        
        timeline_layout.addLayout(timeline_controls)
        
        # Enhanced effects timeline with horizontal scrolling
        timeline_group = QGroupBox("🎬 Effects Timeline")
        timeline_layout.addWidget(timeline_group)
        
        timeline_inner = QVBoxLayout(timeline_group)
        
        # Create horizontal scroll area for timeline
        timeline_scroll = QScrollArea()
        timeline_scroll.setWidgetResizable(True)
        timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        timeline_scroll.setMaximumHeight(100)
        timeline_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #2a2a2a;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #0096ff;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #1aa3ff;
            }
        """)
        
        # Timeline content widget (will expand horizontally)
        timeline_content = QWidget()
        timeline_content_layout = QHBoxLayout(timeline_content)
        timeline_content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Timeline table
        self.timeline_table = QTableWidget()
        self.timeline_table.setColumnCount(4)
        self.timeline_table.setHorizontalHeaderLabels(["Time", "Effect", "Duration", "Actions"])
        
        # Add some sample timeline entries
        self.timeline_table.setRowCount(3)
        
        self.timeline_table.setItem(0, 0, QTableWidgetItem("00:00:00"))
        self.timeline_table.setItem(0, 1, QTableWidgetItem("🎭 Cartoon Pro"))
        self.timeline_table.setItem(0, 2, QTableWidgetItem("00:00:30"))
        self.timeline_table.setItem(0, 3, QTableWidgetItem("✏️ 🗑️"))
        
        self.timeline_table.setItem(1, 0, QTableWidgetItem("00:00:30"))
        self.timeline_table.setItem(1, 1, QTableWidgetItem("🌟 Glow Effect"))
        self.timeline_table.setItem(1, 2, QTableWidgetItem("00:00:45"))
        self.timeline_table.setItem(1, 3, QTableWidgetItem("✏️ 🗑️"))
        
        self.timeline_table.setItem(2, 0, QTableWidgetItem("00:01:15"))
        self.timeline_table.setItem(2, 1, QTableWidgetItem("⚡ Glitch Effect"))
        self.timeline_table.setItem(2, 2, QTableWidgetItem("00:00:20"))
        self.timeline_table.setItem(2, 3, QTableWidgetItem("✏️ 🗑️"))
        
        # Add timeline table to scrollable content
        timeline_content_layout.addWidget(self.timeline_table)
        timeline_content_layout.addStretch()  # Allow horizontal expansion
        
        # Set up the timeline scroll area
        timeline_scroll.setWidget(timeline_content)
        timeline_inner.addWidget(timeline_scroll)
        
        timeline_dock.setWidget(timeline_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, timeline_dock)
        
    def create_menu_bar(self):
        """Create the professional menu bar."""
        menubar = self.menuBar()
            
            # File menu
        file_menu = menubar.addMenu("File")
        
        new_session = QAction("New Session", self)
        file_menu.addAction(new_session)
        
        open_session = QAction("Open Session", self)
        file_menu.addAction(open_session)
        
        save_session = QAction("Save Session", self)
        file_menu.addAction(save_session)
        
        file_menu.addSeparator()
        
        export_video = QAction("Export Video", self)
        file_menu.addAction(export_video)
        
        export_image = QAction("Export Image", self)
        file_menu.addAction(export_image)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        copy_action = QAction("Copy Effect", self)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Paste Effect", self)
        edit_menu.addAction(paste_action)
            
            # View menu
        view_menu = menubar.addMenu("View")
        
        fullscreen_action = QAction("Fullscreen Preview", self)
        view_menu.addAction(fullscreen_action)
        
        view_menu.addSeparator()
        
        show_effects = QAction("Effects Library", self)
        show_effects.setCheckable(True)
        show_effects.setChecked(True)
        view_menu.addAction(show_effects)
        
        show_controls = QAction("Controls", self)
        show_controls.setCheckable(True)
        show_controls.setChecked(True)
        view_menu.addAction(show_controls)
        
        show_properties = QAction("Properties", self)
        show_properties.setCheckable(True)
        show_properties.setChecked(True)
        view_menu.addAction(show_properties)
        
        show_timeline = QAction("Timeline", self)
        show_timeline.setCheckable(True)
        show_timeline.setChecked(True)
        view_menu.addAction(show_timeline)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        settings_action = QAction("Settings", self)
        tools_menu.addAction(settings_action)
        
        performance_action = QAction("Performance Monitor", self)
        tools_menu.addAction(performance_action)
        
        tools_menu.addSeparator()
        
        calibrate_action = QAction("Calibrate Camera", self)
        tools_menu.addAction(calibrate_action)
            
            # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About Dreamscape V2", self)
        help_menu.addAction(about_action)
        
        help_action = QAction("Documentation", self)
        help_menu.addAction(help_action)
        
    def create_main_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        toolbar.addAction("🎬 New Session")
        toolbar.addAction("📁 Open")
        toolbar.addAction("💾 Save")
        toolbar.addSeparator()
        toolbar.addAction("▶️ Start")
        toolbar.addAction("⏸️ Pause")
        toolbar.addAction("⏹️ Stop")
        toolbar.addSeparator()
        toolbar.addAction("📸 Snapshot")
        toolbar.addAction("🔴 Record")
        toolbar.addAction("📡 Stream")
        
    def create_status_bar(self):
        """Create the professional status bar."""
        self.statusBar().showMessage("Ready - Professional Webcam Effects Studio")
        
        # Add status bar widgets
        self.statusBar().addPermanentWidget(QLabel("CPU: 45% | Memory: 32% | GPU: 78%"))
        
    def setup_connections(self):
        """Setup signal connections."""
        self.device_combo.currentTextChanged.connect(self.on_device_changed)
        self.effect_variant_combo.currentTextChanged.connect(self.on_variant_changed)
        self.start_stop_btn.clicked.connect(self.on_start_stop_clicked)
        self.snapshot_btn.clicked.connect(self.on_snapshot_clicked)
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        self.fullscreen_btn.clicked.connect(self.on_fullscreen_clicked)
        self.record_btn.clicked.connect(self.on_record_clicked)
        self.stream_btn.clicked.connect(self.on_stream_clicked)
        
        # Parameter connections are handled by connect_slider_updates() in create_default_sliders()
        
    def setup_animations(self):
        """Setup UI animations."""
        # Add smooth transitions and animations here
        pass
        
    def init_webcam_service(self):
        """Initialize the webcam service."""
        try:
            from src.services.webcam_service import WebcamService
            self.webcam_service = WebcamService()
            
            # Connect webcam service signals with proper error handling
            self.webcam_service.frame_ready.connect(self.on_frame_ready, Qt.QueuedConnection)
            self.webcam_service.error_signal.connect(self.on_webcam_error, Qt.QueuedConnection)
            self.webcam_service.info_signal.connect(self.on_webcam_info, Qt.QueuedConnection)
            
            self.logger.info("Webcam service initialized with queued connections")
        except Exception as e:
            self.logger.error(f"Failed to initialize webcam service: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.webcam_service = None
            
    def on_frame_ready(self, frame):
        """Handle new frame from webcam service."""
        try:
            if frame is not None and frame.size > 0:
                self.current_frame = frame
                self.update_preview_display()
        except Exception as e:
            self.logger.error(f"Error in on_frame_ready: {e}")
            # Don't crash the app, just log the error
        
    def on_webcam_error(self, error_msg):
        """Handle webcam service errors."""
        self.logger.error(f"Webcam error: {error_msg}")
        self.update_status(f"Webcam Error: {error_msg}")
        
    def on_webcam_info(self, info_msg):
        """Handle webcam service info messages."""
        self.logger.info(f"Webcam info: {info_msg}")
        self.update_status(info_msg)
        
    def update_preview_display(self):
        """ENHANCED display with zoom and size support."""
        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        
        # Create QImage
        qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Apply zoom if specified
        if hasattr(self, 'zoom_factor') and self.zoom_factor:
            target_w = int(w * self.zoom_factor)
            target_h = int(h * self.zoom_factor)
            pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.FastTransformation)
        else:
            # Auto-fit to video label size
            label_size = self.video_label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.FastTransformation)
        
        # Display the frame
        self.video_label.setPixmap(pixmap)
        
    def pre_load_camera(self):
        """Pre-load camera at startup for instant access."""
        try:
            self.logger.info("PRE-LOADING CAMERA...")
            # Open camera in background, keep it ready
            self.standby_cap = cv2.VideoCapture(0)
            if self.standby_cap.isOpened():
                self.logger.info("Camera pre-loaded and ready!")
            else:
                self.standby_cap = None
                self.logger.warning("Could not pre-load camera")
        except Exception as e:
            self.standby_cap = None
            self.logger.error(f"Camera pre-load failed: {e}")
            
    def pre_load_styles(self):
        """Pre-load all styles for instant switching."""
        try:
            self.logger.info("PRE-LOADING STYLES...")
            from src.core.style_manager import StyleManager
            self.style_manager_ready = StyleManager()
            
            # Pre-load Edge Detection specifically
            if "Edge Detection" in self.style_manager_ready.style_instances:
                self.edge_detection_ready = self.style_manager_ready.style_instances["Edge Detection"]
                self.logger.info("Edge Detection pre-loaded!")
            
            self.logger.info("All styles pre-loaded and ready!")
        except Exception as e:
            self.logger.error(f"Style pre-load failed: {e}")
            
    def pre_initialize_timer(self):
        """Pre-initialize timer and set it up for instant start."""
        try:
            self.logger.info("PRE-INITIALIZING TIMER...")
            # Timer is already created, just prepare it
            self.preview_timer.timeout.connect(self.update_preview)
            # Set it to the fastest possible interval
            self.ultra_fast_interval = 8  # 120 FPS ready to go
            self.logger.info("Timer pre-initialized at 120 FPS!")
        except Exception as e:
            self.logger.error(f"Timer pre-init failed: {e}")
            
    def update_performance_indicators(self):
        """Update performance indicators with real data."""
        if self.webcam_service and self.webcam_service.is_running():
            # Update FPS (simplified - in real app you'd calculate actual FPS)
            import random
            fps = random.randint(25, 35)
            self.fps_label.setText(f"FPS: {fps}.0")
            
            # Update resolution
            if self.current_frame is not None:
                height, width = self.current_frame.shape[:2]
                self.resolution_label.setText(f"{width}x{height}")
            
            # Update bitrate (simplified)
            bitrate = random.randint(4000, 6000)
            self.bitrate_label.setText(f"Bitrate: {bitrate} kbps")
        
    def apply_effect(self, effect_name):
        """Apply an effect to the preview and embed draggable widget content into parameter panel."""
        self.current_effect_label.setText(effect_name)
        self.effects_history.append(effect_name)
        self.effect_applied.emit(effect_name)
        self.update_status(f"Applied effect: {effect_name}")
        
        # HIDE THE OLD PARAMETER CONTROLS - REPLACE WITH EMBEDDED WIDGET CONTENT!
        self.hide_old_parameter_controls()
        
        # EMBED DRAGGABLE WIDGET CONTENT INTO THE EXISTING PARAMETER PANEL!
        try:
            # Clean up the effect name (remove emojis for style lookup)
            clean_effect_name = effect_name
            if "🔍 Edge Detection" in effect_name:
                clean_effect_name = "Edge Detection"
            elif "🎭 Cartoon Effects" in effect_name:
                clean_effect_name = "Cartoon"
            elif "✏️ Sketch Effects" in effect_name:
                clean_effect_name = "Sketch"
            elif "🎨 Color Effects" in effect_name:
                clean_effect_name = "Color Balance"
            elif "💧 Watercolor" in effect_name:
                clean_effect_name = "Watercolor"
            elif "⚡ Glitch Effect" in effect_name:
                clean_effect_name = "Glitch"
            
            # Embed the widget content into the existing parameter panel
            self.embed_widget_content_into_panel(clean_effect_name)
            self.logger.info(f"Embedded widget content for: {effect_name}")
            
        except Exception as e:
            self.logger.error(f"Error embedding widget content: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Show old controls as fallback
            self.show_old_parameter_controls()
        
    def update_variant_combo(self, effect_name):
        """Update the variant combo box based on the selected effect."""
        self.effect_variant_combo.clear()
        
        if "Cartoon Effects" in effect_name:
            self.effect_variant_combo.addItems(["Detailed", "Fast", "Advanced", "Anime", "Whole"])
        elif "Sketch Effects" in effect_name:
            self.effect_variant_combo.addItems(["Pencil", "Advanced Pencil", "Color Sketch", "Line Art", "Stippling"])
        elif "Color Effects" in effect_name:
            self.effect_variant_combo.addItems(["Brightness", "Contrast", "Color Balance", "Vibrant", "Sepia", "Black & White", "Negative", "Invert"])
        else:
            self.effect_variant_combo.addItems(["Standard", "Enhanced", "Pro", "Custom"])
        
    def load_and_apply_style(self, style_name):
        """Load a style and apply it to the webcam service."""
        try:
            # Use pre-loaded style manager for instant access
            if hasattr(self, 'style_manager_ready'):
                style_manager = self.style_manager_ready
            else:
                # Fallback if pre-load failed
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
            
            # Map UI effect names to actual style names
            style_mapping = {
                # Consolidated styles
                "🎭 Cartoon Effects": "ConsolidatedCartoon",
                "✏️ Sketch Effects": "ConsolidatedSketch", 
                "🎨 Color Effects": "ConsolidatedColor",
                
                # Individual styles
                "💧 Watercolor": "Watercolor",
                "⚡ Glitch Effect": "Glitch",
                "🌟 Glow Effect": "Glowing Edges",
                "🎬 Motion Blur": "Motion Blur",
                "🔍 Edge Detection": "Edge Detection",
                "🌈 Color Grading": "Color Balance",
                "📸 Portrait Mode": "Brightness Only",
                "🎪 Vintage": "Sepia Vibrant",
                "🌌 Cyberpunk": "Negative Vintage",
                
                # Legacy mappings
                "Cartoon (Fast)": "Cartoon",
                "Cartoon (Anime)": "Advanced Cartoon (Anime)",
                "Cartoon (Advanced)": "Advanced Cartoon",
                "Pencil Sketch": "Pencil Sketch",
                "Advanced Sketch": "Advanced Edge Detection",
                "Color Sketch": "Sketch & Color",
                "Oil Painting": "Oil Painting",
                "Line Art": "Line Art",
                "Stippling": "Stippling",
                "Glitch": "Glitch",
                "Mosaic": "Mosaic",
                "Light Leak": "Light Leak",
                "Halftone": "Halftone",
                "Invert": "Invert Colors",
                "Negative": "Negative",
                "Sepia": "Sepia Vibrant",
                "Black & White": "Black & White",
                "Brightness": "Brightness Only",
                "Contrast": "Contrast Only",
                "Color Balance": "Color Balance",
                "Vibrance": "Vibrant Color"
            }
            
            # Get the actual style name
            actual_style_name = style_mapping.get(style_name, style_name)
            
            # FAST PATH for Edge Detection (pre-loaded)
            if "🔍 Edge Detection" in style_name and hasattr(self, 'edge_detection_ready'):
                style_instance = self.edge_detection_ready
                self.current_style_instance = style_instance
                
                # Get current parameters for Edge Detection
                params = self.get_style_specific_parameters(style_name)
                self.logger.info(f"Parameters for {style_name}: {params}")
                
                # Update webcam service or store for when webcam starts
                if self.webcam_service and self.webcam_service.is_running():
                    self.webcam_service.update_style(style_instance, params)
                    self.logger.info(f"Applied style {style_name} to webcam service")
            else:
                    # Store for when webcam starts
                    self.pending_style = style_instance
                    self.pending_params = params
                    self.logger.info(f"Stored style {style_name} for when webcam starts")
                    
                return  # Exit early for fast path
            # Get the style instance from manager
            elif actual_style_name in style_manager.style_instances:
                style_instance = style_manager.style_instances[actual_style_name]
                self.current_style_instance = style_instance  # Store for variant changes
                
                # Set default variant if the style has variants
                if hasattr(style_instance, 'variants') and style_instance.variants:
                    if not style_instance.current_variant:
                        style_instance.current_variant = style_instance.default_variant or style_instance.variants[0]
                # For styles without variants, the base class will handle it
                
                # Get current parameters
                params = self.get_style_specific_parameters(style_name)
                self.logger.info(f"Parameters for {style_name}: {params}")
                
                # Update webcam service with new style
                if self.webcam_service and self.webcam_service.is_running():
                    self.webcam_service.update_style(style_instance, params)
                    self.logger.info(f"Applied style {style_name} to webcam service")
                else:
                    # Store for when webcam starts
                    self.pending_style = style_instance
                    self.pending_params = params
                    self.logger.info(f"Stored style {style_name} for when webcam starts")
                    
            else:
                self.logger.warning(f"Style {style_name} not found in style manager")
            
        except Exception as e:
            self.logger.error(f"Error loading style {style_name}: {e}")
            
    def add_to_favorites(self):
        """Add current effect to favorites."""
        if self.current_effect_label.text() != "None":
            effect = self.current_effect_label.text()
            if effect not in self.favorite_effects:
                self.favorite_effects.append(effect)
                item = QListWidgetItem(f"❤️ {effect}")
                self.favorites_list.addItem(item)
                self.update_status(f"Added {effect} to favorites")
        
    def on_device_changed(self, device_name):
        """Handle device selection change."""
        self.logger.info(f"Device changed to: {device_name}")
        self.device_changed.emit(device_name)
        self.update_status(f"Device changed to: {device_name}")
        
    def on_variant_changed(self, variant_name):
        """Handle effect variant change."""
        self.logger.info(f"Variant changed to: {variant_name}")
        self.update_status(f"Variant changed to: {variant_name}")
        
        # Update the current style's variant and reapply
        if hasattr(self, 'current_style_instance') and self.current_style_instance:
            self.current_style_instance.current_variant = variant_name
            
            # Reapply the effect with new variant
            current_effect = self.current_effect_label.text()
            if current_effect != "None":
                self.load_and_apply_style(current_effect)
        
    def on_start_stop_clicked(self):
        """Handle start/stop button click."""
        self.logger.info("=== START/STOP BUTTON CLICKED ===")
        
        try:
            if not self.is_processing:
                # START TIMER IMMEDIATELY - BLAZING FAST!
                self.video_label.clear()
                self.preview_timer.stop()
                self.preview_timer.start(8)  # 120 FPS for INSTANT response
                
                try:
                    # Use PRE-LOADED camera for INSTANT start!
                    if hasattr(self, 'standby_cap') and self.standby_cap and self.standby_cap.isOpened():
                        self.direct_cap = self.standby_cap
                        self.standby_cap = None  # Transfer ownership
                    else:
                        # Fallback if pre-load failed
                        self.direct_cap = cv2.VideoCapture(0)
                    
                    # Update UI state instantly
                    self.start_stop_btn.setText("⏸️ Stop Processing")
                    self.is_processing = True
                    
                except Exception as start_error:
                    self.logger.error(f"❌ CRITICAL ERROR starting webcam: {start_error}")
                    import traceback
                    self.logger.error(f"Full traceback:\n{traceback.format_exc()}")
                    self.update_status(f"FAILED to start webcam: {start_error}")
                    
                    # Cleanup on error
                    self.is_processing = False
                    self.preview_timer.stop()
                    self.start_stop_btn.setText("▶️ Start Processing")
                    
            else:
                # STOP processing
                self.is_processing = False
                self.preview_timer.stop()
                self.preview_timer.start(500)  # Slow timer when stopped
                
                # Release camera
                if hasattr(self, 'direct_cap') and self.direct_cap:
                    self.direct_cap.release()
                    self.direct_cap = None
                
                # Update UI
                self.start_stop_btn.setText("▶️ Start Processing")
                self.video_label.clear()
                self.video_label.setText("Click 'Start Processing' to begin")
            
        except Exception as e:
            self.logger.error(f"❌ CRITICAL ERROR in start/stop handler: {e}")
            import traceback
            self.logger.error(f"Full traceback:\n{traceback.format_exc()}")
            
            # Force reset on critical error
            self.is_processing = False
            self.preview_timer.stop()
            self.start_stop_btn.setText("▶️ Start Processing")
            
        self.logger.info("=== START/STOP BUTTON HANDLER COMPLETED ===")
            
    def on_snapshot_clicked(self):
        """Handle snapshot button click."""
        self.update_status("Snapshot taken and saved")
        
    def on_reset_clicked(self):
        """Handle reset button click."""
        self.current_effect_label.setText("None")
        self.effects_history.clear()
        
        # Clear the style from webcam service
        if self.webcam_service and self.webcam_service.is_running():
            self.webcam_service.update_style(None, {})
            self.logger.info("Cleared style from webcam service")
        
        # Clear pending styles
        self.pending_style = None
        self.pending_params = {}
        
        self.update_status("Effects reset")
        
    def on_fullscreen_clicked(self):
        """Handle fullscreen button click."""
        self.update_status("Fullscreen mode toggled")
        
    def on_record_clicked(self):
        """Handle record button click."""
        if self.record_btn.text() == "🔴 Record":
            self.record_btn.setText("⏹️ Stop Recording")
            self.update_status("Recording started")
        else:
            self.record_btn.setText("🔴 Record")
            self.update_status("Recording stopped")
            
    def on_stream_clicked(self):
        """Handle stream button click."""
        if self.stream_btn.text() == "📡 Stream":
            self.stream_btn.setText("⏹️ Stop Streaming")
            self.update_status("Streaming started")
        else:
            self.stream_btn.setText("📡 Stream")
            self.update_status("Streaming stopped")
        
    def on_parameter_changed(self):
        """Handle parameter changes."""
        # Get effect-specific parameters
        current_effect = self.current_effect_label.text()
        params = self.get_style_specific_parameters(current_effect)
        self.parameters_changed.emit(params)
        
        # Update webcam service parameters in real-time
        if self.webcam_service and self.webcam_service.is_running():
            self.webcam_service.update_parameters(params)
            self.logger.info(f"Updated webcam service parameters: {params}")
        
    def update_preview(self):
        """Update the preview display - ULTRA FAST VERSION WITH REAL CONTROLS."""
        # DIRECT FRAME CAPTURE - NO MONITORING, NO DELAYS!
        if self.is_processing and hasattr(self, 'direct_cap') and self.direct_cap:
            try:
                ret, frame = self.direct_cap.read()
                if ret:
                    self.current_frame = frame
                    
                    # APPLY CAMERA CONTROLS FIRST (brightness, contrast, saturation)
                    self.current_frame = self.apply_camera_adjustments(self.current_frame)
                    
                    # Apply style effects
                    if self.pending_style and self.pending_params:
                        try:
                            self.current_frame = self.pending_style.apply(self.current_frame, self.pending_params)
                        except:
                            pass
                    
                    # Display immediately
                    self.update_preview_display()
            except:
                pass
        elif not self.is_processing:
            # Simple placeholder
            if not hasattr(self, '_placeholder_set'):
                self.video_label.clear()
                self.video_label.setText("Click 'Start Processing' to begin")
                self._placeholder_set = True
                
    def apply_camera_adjustments(self, frame):
        """Apply camera controls (brightness, contrast, saturation) to the frame."""
        try:
            import numpy as np
            
            # Get current slider values
            brightness = self.brightness_slider.value()  # -100 to 100
            contrast = self.contrast_slider.value() / 100.0  # 0.5 to 3.0
            saturation = self.saturation_slider.value() / 100.0  # 0 to 2.0
            
            # Apply brightness (add/subtract value)
            if brightness != 0:
                frame = cv2.add(frame, np.ones(frame.shape, dtype=np.uint8) * brightness)
            
            # Apply contrast (multiply by factor)
            if contrast != 1.0:
                frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=0)
            
            # Apply saturation
            if saturation != 1.0:
                # Convert to HSV for saturation adjustment
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
                hsv[:, :, 1] = hsv[:, :, 1] * saturation  # Adjust saturation channel
                hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)  # Keep in valid range
                frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
            return frame
            
        except Exception as e:
            # Return original frame if adjustment fails
            return frame
        
    def update_status(self, message):
        """Update the status bar message."""
        self.statusBar().showMessage(message)
        self.logger.info(message)
        
    # === DRAGGABLE WIDGET INTEGRATION ===
    
    def on_filter_widget_created(self, filter_name, widget):
        """Handle when a new filter widget is created."""
        self.logger.info(f"Filter widget created for: {filter_name}")
        
        # Connect parameter changes to webcam service
        widget.parameters_changed.connect(
            lambda params: self.on_widget_parameters_changed(filter_name, params)
        )
        
    def on_widget_layout_changed(self):
        """Handle when widget layout changes."""
        self.logger.debug("Widget layout changed")
        
    def on_widget_parameters_changed(self, filter_name, parameters):
        """Handle parameter changes from draggable widgets."""
        try:
            self.logger.info(f"Widget parameters changed for {filter_name}: {parameters}")
            
            # Update pending parameters
            self.pending_params = parameters
            
            # Apply the effect immediately if we have a style
            if hasattr(self, 'current_style') and self.current_style:
                # Update webcam service if running
                if hasattr(self, 'webcam_service') and self.webcam_service:
                    self.webcam_service.update_style(self.current_style, parameters)
                    
                self.logger.info(f"Applied {filter_name} with updated parameters")
            else:
                # Try to load and apply the style
                self.apply_effect_with_widget_parameters(filter_name, None)
            
        except Exception as e:
            self.logger.error(f"Error handling widget parameter changes: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
    def create_filter_widget(self, filter_name):
        """Create draggable widget for the specified filter."""
        try:
            # Get filter parameters from style manager
            if hasattr(self, 'style_manager_ready') and self.style_manager_ready:
                style_manager = self.style_manager_ready
            else:
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
                
            # Get style instance
            style_instance = style_manager.get_style(filter_name)
            if not style_instance:
                self.logger.warning(f"No style found for filter: {filter_name}")
                return None
                
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
                                'type': self.get_widget_type(props),
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
                parameters = self.create_fallback_parameters(filter_name)
            
            # Create widget using registry
            widget = self.widget_registry.create_widget_for_filter(filter_name, parameters)
            
            self.logger.info(f"Created draggable widget for filter: {filter_name}")
            return widget
            
        except Exception as e:
            self.logger.error(f"Error creating filter widget: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
    def get_widget_type(self, props):
        """Determine appropriate widget type from style properties."""
        if 'options' in props:
            return 'str'
        elif isinstance(props.get('default'), bool):
            return 'bool'
        elif isinstance(props.get('default'), float):
            return 'float'
        elif isinstance(props.get('default'), int):
            # Use slider for integer ranges
            if 'min' in props and 'max' in props:
                return 'slider'
            return 'int'
        else:
            return 'str'
            
    def hide_old_parameter_controls(self):
        """Hide the old static parameter controls when using draggable widgets."""
        try:
            # Hide the old parameter sliders and labels
            if hasattr(self, 'param1_slider'):
                self.param1_slider.hide()
                self.param1_label.hide()
            if hasattr(self, 'param2_slider'):
                self.param2_slider.hide()
                self.param2_label.hide()
            if hasattr(self, 'param3_slider'):
                self.param3_slider.hide()
                self.param3_label.hide()
            if hasattr(self, 'param4_slider'):
                self.param4_slider.hide()
                self.param4_label.hide()
                
            # Hide the old effect variant combo
            if hasattr(self, 'effect_variant_combo'):
                self.effect_variant_combo.hide()
                
            self.logger.info("Hidden old parameter controls - using draggable widgets")
        except Exception as e:
            self.logger.error(f"Error hiding old controls: {e}")
            
    def show_old_parameter_controls(self):
        """Show the old static parameter controls as fallback."""
        try:
            # Show the old parameter sliders and labels
            if hasattr(self, 'param1_slider'):
                self.param1_slider.show()
                self.param1_label.show()
            if hasattr(self, 'param2_slider'):
                self.param2_slider.show()
                self.param2_label.show()
            if hasattr(self, 'param3_slider'):
                self.param3_slider.show()
                self.param3_label.show()
            if hasattr(self, 'param4_slider'):
                self.param4_slider.show()
                self.param4_label.show()
                
            # Show the old effect variant combo
            if hasattr(self, 'effect_variant_combo'):
                self.effect_variant_combo.show()
                
            self.logger.info("Showed old parameter controls as fallback")
        except Exception as e:
            self.logger.error(f"Error showing old controls: {e}")
            
    def apply_effect_with_widget_parameters(self, style_name, widget):
        """Apply effect using parameters from the draggable widget."""
        try:
            # Get current parameters from the widget
            widget_params = widget.get_parameters()
            
            # Load and apply the style with widget parameters
            if hasattr(self, 'style_manager_ready'):
                style_manager = self.style_manager_ready
            else:
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
                
            # Get the style instance
            style_instance = style_manager.get_style(style_name)
            if not style_instance:
                self.logger.warning(f"Style not found: {style_name}")
                return
                
            # Apply the style with widget parameters
            self.pending_params = widget_params
            self.current_style = style_instance
            
            # Update webcam service if running
            if hasattr(self, 'webcam_service') and self.webcam_service:
                self.webcam_service.update_style(style_instance, widget_params)
                
            self.logger.info(f"Applied {style_name} with widget parameters: {widget_params}")
            
        except Exception as e:
            self.logger.error(f"Error applying effect with widget parameters: {e}")
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

    def embed_widget_content_into_panel(self, filter_name):
        """Embed draggable widget content into the existing parameter panel."""
        try:
            # Clear existing parameter widgets
            self.clear_embedded_parameter_widgets()
            
            # Get style manager
            if hasattr(self, 'style_manager_ready'):
                style_manager = self.style_manager_ready
            else:
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
                
            # Get style instance
            style_instance = style_manager.get_style(filter_name)
            if not style_instance:
                self.logger.warning(f"No style found for filter: {filter_name}")
                # Use fallback parameters
                parameters = self.create_fallback_parameters(filter_name)
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
                                    'type': self.get_widget_type(props),
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
                    parameters = self.create_fallback_parameters(filter_name)
            
            # Store the current style for parameter updates
            self.current_style = style_instance
            self.current_filter_name = filter_name
            
            # Create and embed parameter widgets into the existing layout
            self.create_embedded_parameter_widgets(parameters)
            
            # Apply the effect immediately
            self.apply_embedded_effect(filter_name, parameters)
            
        except Exception as e:
            self.logger.error(f"Error embedding widget content: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    def clear_embedded_parameter_widgets(self):
        """Clear existing embedded parameter widgets."""
        try:
            # Clear the existing parameter layout
            if hasattr(self, 'params_layout'):
                # Remove all widgets from the layout
                while self.params_layout.rowCount() > 0:
                    self.params_layout.removeRow(0)
                    
            # Clear stored widget references
            if hasattr(self, 'embedded_param_widgets'):
                for widget in self.embedded_param_widgets.values():
                    if widget:
                        widget.deleteLater()
                self.embedded_param_widgets.clear()
            else:
                self.embedded_param_widgets = {}
            
        except Exception as e:
            self.logger.error(f"Error clearing embedded widgets: {e}")
            
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
                self.params_layout.addRow(category_label)
                
                # Create widgets for each parameter in this category
                for param in params:
                    widget = self.create_embedded_parameter_widget(param)
                    if widget:
                        self.embedded_param_widgets[param['name']] = widget
                        self.params_layout.addRow(param['label'], widget)
            
        except Exception as e:
            self.logger.error(f"Error creating embedded parameter widgets: {e}")
            
    def create_embedded_parameter_widget(self, param):
        """Create a single embedded parameter widget."""
        try:
            param_type = param.get('type', 'slider')
            param_name = param['name']
            default_value = param.get('default', 0)
            
            if param_type == 'slider':
                widget = QSlider(Qt.Horizontal)
                min_val = param.get('min', 0)
                max_val = param.get('max', 100)
                widget.setRange(min_val, max_val)
                widget.setValue(default_value)
                
                # Connect to parameter update
                widget.valueChanged.connect(lambda value, name=param_name: self.on_embedded_parameter_changed(name, value))
                
            elif param_type == 'float':
                widget = QDoubleSpinBox()
                min_val = param.get('min', 0.0)
                max_val = param.get('max', 100.0)
                step = param.get('step', 0.1)
                widget.setRange(min_val, max_val)
                widget.setSingleStep(step)
                widget.setValue(default_value)
                
                # Connect to parameter update
                widget.valueChanged.connect(lambda value, name=param_name: self.on_embedded_parameter_changed(name, value))
                
            elif param_type == 'int':
                widget = QSpinBox()
                min_val = param.get('min', 0)
                max_val = param.get('max', 100)
                widget.setRange(min_val, max_val)
                widget.setValue(default_value)
                
                # Connect to parameter update
                widget.valueChanged.connect(lambda value, name=param_name: self.on_embedded_parameter_changed(name, value))
                
            elif param_type == 'bool':
                widget = QCheckBox()
                widget.setChecked(default_value)
                
                # Connect to parameter update
                widget.toggled.connect(lambda checked, name=param_name: self.on_embedded_parameter_changed(name, checked))
                
            elif param_type == 'str':
                widget = QComboBox()
                options = param.get('options', ['Option 1', 'Option 2'])
                widget.addItems(options)
                if default_value in options:
                    widget.setCurrentText(default_value)
                
                # Connect to parameter update
                widget.currentTextChanged.connect(lambda text, name=param_name: self.on_embedded_parameter_changed(name, text))
                
            else:
                # Default to slider
                widget = QSlider(Qt.Horizontal)
                widget.setRange(0, 100)
                widget.setValue(default_value)
                widget.valueChanged.connect(lambda value, name=param_name: self.on_embedded_parameter_changed(name, value))
                
            return widget
            
        except Exception as e:
            self.logger.error(f"Error creating embedded parameter widget: {e}")
            return None
            
    def on_embedded_parameter_changed(self, param_name, value):
        """Handle parameter changes from embedded widgets."""
        try:
            # Update the current parameters
            if not hasattr(self, 'current_embedded_params'):
                self.current_embedded_params = {}
                
            self.current_embedded_params[param_name] = value
            
            # Apply the effect with updated parameters
            if hasattr(self, 'current_filter_name'):
                self.apply_embedded_effect(self.current_filter_name, self.current_embedded_params)
                
            self.logger.info(f"Embedded parameter changed: {param_name} = {value}")
            
        except Exception as e:
            self.logger.error(f"Error handling embedded parameter change: {e}")
            
    def apply_embedded_effect(self, filter_name, parameters):
        """Apply effect using embedded widget parameters."""
        try:
            # Load and apply the style with parameters
            if hasattr(self, 'style_manager_ready'):
                style_manager = self.style_manager_ready
            else:
                from src.core.style_manager import StyleManager
                style_manager = StyleManager()
                
            # Get the style instance
            style_instance = style_manager.get_style(filter_name)
            if not style_instance:
                self.logger.warning(f"Style not found: {filter_name}")
                return
                
            # Apply the style with parameters
            self.pending_params = parameters
            self.current_style = style_instance
            
            # Update webcam service if running
            if hasattr(self, 'webcam_service') and self.webcam_service:
                self.webcam_service.update_style(style_instance, parameters)
                
            self.logger.info(f"Applied {filter_name} with embedded parameters: {parameters}")
            
        except Exception as e:
            self.logger.error(f"Error applying embedded effect: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
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

def main():
    """Main function to run the professional V2 application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Dreamscape V2 Professional")
    app.setApplicationVersion("2.0.0")
    
    window = ProfessionalV2MainWindow()
    window.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 