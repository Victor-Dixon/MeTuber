"""
Text Renderer Module for Video Overlay

Handles rendering transcribed text as an overlay on video frames with
customizable styling and animation effects.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import time

@dataclass
class TextStyle:
    """Text styling configuration."""
    font_family: str = "Arial"
    font_size: int = 32
    font_color: Tuple[int, int, int] = (255, 255, 255)  # White
    background_color: Optional[Tuple[int, int, int]] = (0, 0, 0)  # Black
    background_opacity: float = 0.7
    outline_color: Optional[Tuple[int, int, int]] = (0, 0, 0)  # Black outline
    outline_width: int = 2
    padding: int = 10
    corner_radius: int = 5
    shadow_offset: Tuple[int, int] = (2, 2)
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_blur: int = 3

@dataclass
class AnimationConfig:
    """Animation configuration."""
    fade_in_duration: float = 0.3
    fade_out_duration: float = 0.5
    typing_speed: float = 0.05  # seconds per character
    scroll_speed: float = 1.0   # pixels per second
    bounce_amplitude: float = 5.0
    bounce_frequency: float = 2.0

class TextRenderer:
    """Renders text overlays on video frames."""
    
    def __init__(self):
        """Initialize text renderer."""
        self.logger = logging.getLogger(__name__)
        self.style = TextStyle()
        self.animation = AnimationConfig()
        
        # Text state
        self.current_text = ""
        self.text_history = []
        self.max_history = 5
        
        # Animation state
        self.text_start_time = 0
        self.typing_index = 0
        self.fade_alpha = 0.0
        self.is_visible = False
        
        # Font cache (limited size to prevent memory leaks)
        self.font_cache = {}
        self.max_font_cache_size = 50
        
        # Face detection for smart positioning
        self.face_detector = None
        self.enable_face_detection = True
        self._initialize_face_detection()
        
        self.logger.info("TextRenderer initialized")
    
    def set_style(self, style: TextStyle):
        """Set text styling."""
        self.style = style
    
    def set_animation(self, animation: AnimationConfig):
        """Set animation configuration."""
        self.animation = animation
    
    def update_text(self, text: str):
        """Update the current text to display."""
        if text != self.current_text:
            self.current_text = text
            self.text_start_time = time.time()
            self.typing_index = 0
            self.fade_alpha = 0.0
            self.is_visible = True
            
            # Add to history
            if text.strip():
                self.text_history.append({
                    'text': text,
                    'timestamp': time.time()
                })
                
                # Keep only recent history
                if len(self.text_history) > self.max_history:
                    self.text_history.pop(0)
    
    def render_overlay(self, frame: np.ndarray, position: Tuple[int, int] = None) -> np.ndarray:
        """
        Render text overlay on video frame.
        
        Args:
            frame: Input video frame (BGR format)
            position: Text position (x, y) - None for auto-positioning
            
        Returns:
            Frame with text overlay
        """
        try:
            if not self.current_text or not self.is_visible:
                return frame
            
            # Update animation state
            self._update_animation_state()
            
            # Get display text (with typing effect)
            display_text = self._get_display_text()
            
            if not display_text:
                return frame
            
            # Determine position
            if position is None:
                position = self._calculate_position(frame)
            
            # Create text image
            text_image = self._create_text_image(display_text)
            
            if text_image is None:
                return frame
            
            # Apply fade effect
            if self.fade_alpha < 1.0:
                text_image = self._apply_fade_effect(text_image)
            
            # Overlay on frame
            result_frame = self._overlay_text(frame, text_image, position)
            
            return result_frame
            
        except Exception as e:
            self.logger.error(f"Error rendering text overlay: {e}")
            return frame
    
    def _update_animation_state(self):
        """Update animation state based on time."""
        current_time = time.time()
        elapsed = current_time - self.text_start_time
        
        # Update typing effect
        if self.animation.typing_speed > 0:
            target_chars = int(elapsed / self.animation.typing_speed)
            self.typing_index = min(target_chars, len(self.current_text))
        
        # Update fade effect
        if elapsed < self.animation.fade_in_duration:
            # Fade in
            self.fade_alpha = elapsed / self.animation.fade_in_duration
        elif len(self.current_text) > 0 and elapsed > 3.0:  # Show for 3 seconds
            # Fade out
            fade_out_start = 3.0
            fade_out_elapsed = elapsed - fade_out_start
            if fade_out_elapsed < self.animation.fade_out_duration:
                self.fade_alpha = 1.0 - (fade_out_elapsed / self.animation.fade_out_duration)
            else:
                self.is_visible = False
                self.fade_alpha = 0.0
        else:
            # Fully visible
            self.fade_alpha = 1.0
    
    def _get_display_text(self) -> str:
        """Get text to display (with typing effect)."""
        if self.animation.typing_speed > 0:
            return self.current_text[:self.typing_index]
        else:
            return self.current_text
    
    def _initialize_face_detection(self):
        """Initialize face detection cascade."""
        try:
            # Try to load OpenCV's face detection cascade
            import cv2
            import os
            
            # Try multiple possible paths for the cascade file
            cascade_paths = [
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
                os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml'),
                'haarcascade_frontalface_default.xml'
            ]
            
            for path in cascade_paths:
                try:
                    if os.path.exists(path):
                        self.face_detector = cv2.CascadeClassifier(path)
                        if not self.face_detector.empty():
                            self.logger.info(f"Face detection initialized from: {path}")
                            return
                except Exception as e:
                    self.logger.debug(f"Failed to load cascade from {path}: {e}")
                    continue
            
            self.logger.warning("Face detection cascade not found. Smart positioning disabled.")
            self.enable_face_detection = False
            self.face_detector = None
            
        except Exception as e:
            self.logger.warning(f"Could not initialize face detection: {e}")
            self.enable_face_detection = False
            self.face_detector = None
    
    def _detect_faces(self, frame: np.ndarray) -> list:
        """Detect faces in the frame."""
        try:
            if not self.enable_face_detection or self.face_detector is None:
                return []
            
            import cv2
            
            # Convert to grayscale for face detection
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Detect faces
            faces = self.face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # Convert to list of (x, y, w, h) tuples
            return [tuple(face) for face in faces]
            
        except Exception as e:
            self.logger.debug(f"Error detecting faces: {e}")
            return []
    
    def _calculate_position(self, frame: np.ndarray) -> Tuple[int, int]:
        """Calculate optimal text position on frame, avoiding faces."""
        height, width = frame.shape[:2]
        
        # Default position: bottom center
        x = width // 2
        y = height - 100
        
        # Detect faces if enabled
        if self.enable_face_detection:
            faces = self._detect_faces(frame)
            
            if faces:
                # Calculate safe regions (avoid faces)
                # Text dimensions (estimated - will be refined after text is created)
                text_height_estimate = self.style.font_size + (self.style.padding * 2) + 20
                text_width_estimate = width // 2  # Estimate half width for typical caption
                
                # Get face regions (convert to bottom-y coordinates for easier comparison)
                face_regions = []
                for (fx, fy, fw, fh) in faces:
                    # Face extends from fy to fy+fh
                    # Add margin around faces
                    margin = 20
                    face_regions.append({
                        'top': max(0, fy - margin),
                        'bottom': min(height, fy + fh + margin),
                        'left': max(0, fx - margin),
                        'right': min(width, fx + fw + margin),
                        'center_y': fy + fh // 2,
                        'center_x': fx + fw // 2
                    })
                
                # Try different positions, prioritizing bottom center
                candidate_positions = [
                    (width // 2, height - text_height_estimate - 20),  # Bottom center (default)
                    (width // 2, text_height_estimate + 20),  # Top center
                    (text_width_estimate // 2 + 20, height // 2),  # Left middle
                    (width - text_width_estimate // 2 - 20, height // 2),  # Right middle
                ]
                
                # Score each position based on distance from faces
                best_position = candidate_positions[0]
                best_score = float('inf')
                
                for pos_x, pos_y in candidate_positions:
                    # Check if position overlaps with any face region
                    overlaps_face = False
                    for face in face_regions:
                        text_top = pos_y - text_height_estimate // 2
                        text_bottom = pos_y + text_height_estimate // 2
                        text_left = pos_x - text_width_estimate // 2
                        text_right = pos_x + text_width_estimate // 2
                        
                        # Check for overlap
                        if not (text_bottom < face['top'] or text_top > face['bottom'] or
                               text_right < face['left'] or text_left > face['right']):
                            overlaps_face = True
                            break
                    
                    if not overlaps_face:
                        # Calculate distance from nearest face
                        min_distance = float('inf')
                        for face in face_regions:
                            # Distance from text center to face center
                            distance = ((pos_x - face['center_x'])**2 + (pos_y - face['center_y'])**2)**0.5
                            min_distance = min(min_distance, distance)
                        
                        # Prefer positions farther from faces
                        if min_distance < best_score:
                            best_score = min_distance
                            best_position = (pos_x, pos_y)
                
                # If we found a good position, use it
                if best_score < float('inf'):
                    x, y = best_position
                    self.logger.debug(f"Smart positioning: ({x}, {y}) avoiding {len(faces)} face(s)")
                else:
                    # All positions overlap faces, use top position as fallback
                    x, y = width // 2, text_height_estimate + 20
                    self.logger.debug(f"All positions overlap faces, using top position: ({x}, {y})")
        
        return (x, y)
    
    def _create_text_image(self, text: str) -> Optional[np.ndarray]:
        """Create image with rendered text."""
        try:
            if not text.strip():
                return None
            
            # Get font
            font = self._get_font()
            if font is None:
                return None
            
            # Get text size
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Add padding
            total_width = text_width + (self.style.padding * 2)
            total_height = text_height + (self.style.padding * 2)
            
            # Create image with alpha channel
            image = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw background if specified
            if self.style.background_color:
                background_alpha = int(255 * self.style.background_opacity)
                background_color = (*self.style.background_color, background_alpha)
                
                # Draw rounded rectangle background
                draw.rounded_rectangle(
                    [0, 0, total_width, total_height],
                    radius=self.style.corner_radius,
                    fill=background_color
                )
            
            # Draw shadow if specified
            if self.style.shadow_offset != (0, 0):
                shadow_x = self.style.padding + self.style.shadow_offset[0]
                shadow_y = self.style.padding + self.style.shadow_offset[1]
                draw.text(
                    (shadow_x, shadow_y),
                    text,
                    font=font,
                    fill=(*self.style.shadow_color, 128)
                )
            
            # Draw outline if specified
            if self.style.outline_color and self.style.outline_width > 0:
                for dx in range(-self.style.outline_width, self.style.outline_width + 1):
                    for dy in range(-self.style.outline_width, self.style.outline_width + 1):
                        if dx*dx + dy*dy <= self.style.outline_width*self.style.outline_width:
                            draw.text(
                                (self.style.padding + dx, self.style.padding + dy),
                                text,
                                font=font,
                                fill=(*self.style.outline_color, 255)
                            )
            
            # Draw main text
            draw.text(
                (self.style.padding, self.style.padding),
                text,
                font=font,
                fill=(*self.style.font_color, 255)
            )
            
            # Convert to numpy array (BGR format for OpenCV)
            text_image = np.array(image)
            text_image = cv2.cvtColor(text_image, cv2.COLOR_RGBA2BGRA)
            
            return text_image
            
        except Exception as e:
            self.logger.error(f"Error creating text image: {e}")
            return None
    
    def _get_font(self) -> Optional[ImageFont.FreeTypeFont]:
        """Get font for text rendering."""
        try:
            font_key = f"{self.style.font_family}_{self.style.font_size}"
            
            if font_key not in self.font_cache:
                # Limit cache size to prevent memory leaks
                if len(self.font_cache) >= self.max_font_cache_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self.font_cache))
                    del self.font_cache[oldest_key]
                
                # Try to load font
                try:
                    font = ImageFont.truetype(self.style.font_family, self.style.font_size)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                
                self.font_cache[font_key] = font
            
            return self.font_cache[font_key]
            
        except Exception as e:
            self.logger.error(f"Error loading font: {e}")
            return None
    
    def _apply_fade_effect(self, text_image: np.ndarray) -> np.ndarray:
        """Apply fade effect to text image."""
        try:
            if self.fade_alpha >= 1.0:
                return text_image
            
            # Apply alpha blending
            alpha_channel = text_image[:, :, 3].astype(np.float32)
            alpha_channel *= self.fade_alpha
            text_image[:, :, 3] = alpha_channel.astype(np.uint8)
            
            return text_image
            
        except Exception as e:
            self.logger.error(f"Error applying fade effect: {e}")
            return text_image
    
    def _overlay_text(self, frame: np.ndarray, text_image: np.ndarray, position: Tuple[int, int]) -> np.ndarray:
        """Overlay text image on video frame."""
        try:
            # Convert frame to RGBA if needed
            if frame.shape[2] == 3:
                frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            else:
                frame_rgba = frame.copy()
            
            # Calculate position (center text horizontally)
            x, y = position
            text_height, text_width = text_image.shape[:2]
            x = x - text_width // 2
            y = y - text_height // 2
            
            # Ensure position is within frame bounds
            x = max(0, min(x, frame_rgba.shape[1] - text_width))
            y = max(0, min(y, frame_rgba.shape[0] - text_height))
            
            # Extract region of interest
            roi = frame_rgba[y:y+text_height, x:x+text_width]
            
            # Blend text image with ROI
            alpha = text_image[:, :, 3:4].astype(np.float32) / 255.0
            alpha = np.repeat(alpha, 3, axis=2)
            
            blended = (text_image[:, :, :3].astype(np.float32) * alpha + 
                      roi[:, :, :3].astype(np.float32) * (1 - alpha))
            
            # Update ROI
            roi[:, :, :3] = blended.astype(np.uint8)
            
            # Convert back to BGR if original was BGR
            if frame.shape[2] == 3:
                result = cv2.cvtColor(frame_rgba, cv2.COLOR_BGRA2BGR)
            else:
                result = frame_rgba
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error overlaying text: {e}")
            return frame
    
    def clear_text(self):
        """Clear current text."""
        self.current_text = ""
        self.is_visible = False
        self.fade_alpha = 0.0
        self.logger.debug("Text cleared")
    
    def get_text_history(self) -> list:
        """Get text history."""
        return self.text_history.copy()
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.font_cache.clear()
            self.text_history.clear()
            self.logger.info("TextRenderer cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup() 