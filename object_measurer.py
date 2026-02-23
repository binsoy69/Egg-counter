"""
Object Measurement System using Webcam
======================================
Measures real-world dimensions of flat objects using a USB webcam
with A4 paper calibration for accurate pixel-to-mm conversion.

Author: AI Assistant
Dependencies: OpenCV, NumPy

Usage:
    python object_measurer.py
    
Controls:
    c - Calibrate using A4 paper (must be visible in frame)
    r - Reset calibration
    q - Quit application

Accuracy Tips:
    1. Position camera perpendicular to the surface (looking straight down)
    2. Use diffuse lighting to avoid harsh shadows
    3. Use a contrasting solid-color background (dark objects on light, vice versa)
    4. Keep A4 paper and objects flat on the surface
    5. Recalibrate when camera position or height changes
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List
import time


# A4 paper dimensions in millimeters
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0

# ============================================================
# CAMERA CONFIGURATION - Edit these settings as needed
# ============================================================
CAMERA_INDEX = 1          # 0 = built-in camera, 1 = first USB webcam, 2 = second USB webcam
CAMERA_RESOLUTION = (640, 480)  # Use standard resolutions: 640x480, 1280x720, 1920x1080
WINDOW_SIZE = (800, 450)  # Display window size (smaller for screen convenience)
DEBUG_MODE = False        # Set to True to see edge detection overlay (press 'd' to toggle)
# ============================================================


@dataclass
class CalibrationData:
    """Stores calibration information."""
    pixels_per_mm: float
    calibration_time: float
    a4_contour: np.ndarray


class ImagePreprocessor:
    """Handles image preprocessing for robust detection under variable lighting."""
    
    def __init__(self):
        # CLAHE for contrast enhancement
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame to handle variable lighting conditions.
        Uses LAB color space and adaptive histogram equalization.
        """
        # Convert to LAB color space (better for varying lighting)
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # Apply CLAHE to L channel for contrast enhancement
        l_enhanced = self.clahe.apply(l_channel)
        
        # Merge back
        lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        return blurred
    
    def get_edges(self, preprocessed: np.ndarray) -> np.ndarray:
        """
        Get edges using adaptive thresholding for robustness.
        """
        # Adaptive thresholding handles varying illumination
        thresh = cv2.adaptiveThreshold(
            preprocessed, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        # Morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Canny edge detection on the thresholded image
        edges = cv2.Canny(thresh, 50, 150)
        
        # Dilate edges to close small gaps
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        return edges


class A4Detector:
    """Detects A4 paper for calibration."""
    
    def __init__(self, preprocessor: ImagePreprocessor):
        self.preprocessor = preprocessor
    
    def detect(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect A4 paper in frame and return its corner points.
        Returns None if no suitable rectangle found.
        """
        preprocessed = self.preprocessor.preprocess(frame)
        edges = self.preprocessor.get_edges(preprocessed)
        
        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return None
        
        # Sort contours by area (largest first)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        frame_area = frame.shape[0] * frame.shape[1]
        
        for contour in contours[:10]:  # Check top 10 largest contours
            area = cv2.contourArea(contour)
            
            # A4 paper should occupy a reasonable portion of the frame
            if area < frame_area * 0.02:  # At least 2% of frame (relaxed)
                continue
            
            # Approximate the contour to a polygon with more tolerance
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)  # More tolerance
            
            # We're looking for a quadrilateral (4 corners)
            if len(approx) == 4:
                # Check if it's roughly rectangular (A4 aspect ratio ~1:1.414)
                rect = cv2.minAreaRect(contour)
                width, height = rect[1]
                
                if width == 0 or height == 0:
                    continue
                
                aspect_ratio = max(width, height) / min(width, height)
                
                # Allow wide tolerance for perspective distortion
                if 1.1 < aspect_ratio < 2.0:
                    return self._order_points(approx.reshape(4, 2))
        
        # Fallback: try using the largest rectangular contour
        for contour in contours[:10]:
            area = cv2.contourArea(contour)
            if area < frame_area * 0.02:
                continue
            
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            width, height = rect[1]
            
            if width == 0 or height == 0:
                continue
            
            aspect_ratio = max(width, height) / min(width, height)
            if 1.1 < aspect_ratio < 2.0:
                return self._order_points(box)
        
        return None
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        Order points in: top-left, top-right, bottom-right, bottom-left order.
        """
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Sum of coordinates: top-left has smallest, bottom-right has largest
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Difference: top-right has smallest, bottom-left has largest
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect


class CameraCalibrator:
    """Handles camera calibration using A4 paper reference."""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.a4_detector = A4Detector(self.preprocessor)
        self.calibration: Optional[CalibrationData] = None
    
    def calibrate(self, frame: np.ndarray) -> bool:
        """
        Calibrate using A4 paper visible in frame.
        Returns True if calibration successful.
        """
        corners = self.a4_detector.detect(frame)
        
        if corners is None:
            return False
        
        # Calculate the pixel dimensions of the detected A4 paper
        # Use the average of both edge pairs for better accuracy
        width_top = np.linalg.norm(corners[1] - corners[0])
        width_bottom = np.linalg.norm(corners[2] - corners[3])
        height_left = np.linalg.norm(corners[3] - corners[0])
        height_right = np.linalg.norm(corners[2] - corners[1])
        
        avg_width_px = (width_top + width_bottom) / 2
        avg_height_px = (height_left + height_right) / 2
        
        # Calculate pixels per mm (average of width and height measurements)
        px_per_mm_width = avg_width_px / A4_WIDTH_MM
        px_per_mm_height = avg_height_px / A4_HEIGHT_MM
        pixels_per_mm = (px_per_mm_width + px_per_mm_height) / 2
        
        self.calibration = CalibrationData(
            pixels_per_mm=pixels_per_mm,
            calibration_time=time.time(),
            a4_contour=corners
        )
        
        return True
    
    def reset(self):
        """Reset calibration."""
        self.calibration = None
    
    def is_calibrated(self) -> bool:
        """Check if system is calibrated."""
        return self.calibration is not None
    
    def pixels_to_mm(self, pixels: float) -> float:
        """Convert pixel measurement to millimeters."""
        if self.calibration is None:
            return 0.0
        return pixels / self.calibration.pixels_per_mm


class ObjectDetector:
    """Detects WHITE objects and measures their dimensions."""
    
    def __init__(self, calibrator: CameraCalibrator):
        self.calibrator = calibrator
        self.min_area = 2000  # Minimum contour area (increase to reduce noise)
        self.min_brightness = 180  # Minimum brightness to consider "white" (0-255)
    
    def detect_objects(self, frame: np.ndarray) -> List[dict]:
        """
        Detect WHITE objects in frame and return their measurements.
        Uses HSV color space to isolate white/bright regions.
        """
        if not self.calibrator.is_calibrated():
            return []
        
        # Convert to HSV for better white detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # White objects have low saturation and high value
        # H: any, S: 0-50 (low saturation), V: 180-255 (high brightness)
        lower_white = np.array([0, 0, self.min_brightness])
        upper_white = np.array([180, 60, 255])
        
        # Create mask for white regions
        white_mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Find contours in the white mask
        contours, _ = cv2.findContours(
            white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        objects = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < self.min_area:
                continue
            
            # Skip if this might be the A4 paper itself (calibration reference)
            if self.calibrator.calibration is not None:
                a4_area = cv2.contourArea(self.calibrator.calibration.a4_contour.astype(np.float32))
                if abs(area - a4_area) / a4_area < 0.3:  # Within 30% of A4 area
                    continue
            
            # Get minimum area bounding rectangle
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.intp(box)
            
            # Get dimensions
            width_px, height_px = rect[1]
            if width_px == 0 or height_px == 0:
                continue
            
            # Ensure width is the smaller dimension
            if width_px > height_px:
                width_px, height_px = height_px, width_px
            
            # Convert to mm
            width_mm = self.calibrator.pixels_to_mm(width_px)
            height_mm = self.calibrator.pixels_to_mm(height_px)
            
            # Skip very small measurements (noise)
            if width_mm < 5 or height_mm < 5:
                continue
            
            # Get center point
            center = (int(rect[0][0]), int(rect[0][1]))
            
            objects.append({
                'contour': contour,
                'box': box,
                'center': center,
                'width_mm': width_mm,
                'height_mm': height_mm,
                'width_px': width_px,
                'height_px': height_px,
                'angle': rect[2]
            })
        
        return objects


class MeasurementOverlay:
    """Draws measurement overlays on the frame."""
    
    # Colors (BGR format) - more visible colors
    COLOR_CALIBRATED = (0, 255, 0)       # Green
    COLOR_NOT_CALIBRATED = (0, 0, 255)   # Red
    COLOR_OBJECT_BOX = (0, 255, 255)     # Cyan - more visible
    COLOR_MEASUREMENT = (0, 0, 0)        # Black text (on white bg)
    COLOR_A4_OUTLINE = (255, 0, 255)     # Magenta
    COLOR_TEXT_BG = (255, 255, 255)      # White background
    
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7  # Larger text
        self.thickness = 2
    
    def draw_status(self, frame: np.ndarray, calibrator: CameraCalibrator, fps: float):
        """Draw calibration status and FPS."""
        h, w = frame.shape[:2]
        
        # Status bar background
        cv2.rectangle(frame, (0, 0), (w, 35), (40, 40, 40), -1)
        
        # Calibration status
        if calibrator.is_calibrated():
            status = f"CALIBRATED ({calibrator.calibration.pixels_per_mm:.2f} px/mm)"
            color = self.COLOR_CALIBRATED
        else:
            status = "NOT CALIBRATED - Press 'c' with A4 paper visible"
            color = self.COLOR_NOT_CALIBRATED
        
        cv2.putText(frame, status, (10, 25), self.font, 0.5, color, 1)
        
        # FPS
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(frame, fps_text, (w - 100, 25), self.font, 0.5, (255, 255, 255), 1)
        
        # Controls hint
        cv2.putText(frame, "c:Calibrate | r:Reset | q:Quit", 
                    (10, h - 10), self.font, 0.4, (180, 180, 180), 1)
    
    def draw_a4_outline(self, frame: np.ndarray, calibrator: CameraCalibrator):
        """Draw outline of detected A4 paper."""
        if calibrator.calibration is None:
            return
        
        pts = calibrator.calibration.a4_contour.astype(np.int32)
        cv2.polylines(frame, [pts], True, self.COLOR_A4_OUTLINE, 2)
        
        # Label
        center = np.mean(pts, axis=0).astype(int)
        cv2.putText(frame, "A4 Reference", (center[0] - 50, center[1]),
                    self.font, 0.5, self.COLOR_A4_OUTLINE, 1)
    
    def draw_object_measurements(self, frame: np.ndarray, objects: List[dict]):
        """Draw bounding boxes and measurements for detected objects."""
        for i, obj in enumerate(objects):
            # Draw bounding box (thicker for visibility)
            cv2.drawContours(frame, [obj['box']], 0, self.COLOR_OBJECT_BOX, 3)
            
            # Draw measurement labels
            center = obj['center']
            width_mm = obj['width_mm']
            height_mm = obj['height_mm']
            
            # Background for text
            label = f"{width_mm:.1f} x {height_mm:.1f} mm"
            (text_w, text_h), _ = cv2.getTextSize(label, self.font, self.font_scale, self.thickness)
            
            text_x = center[0] - text_w // 2
            text_y = center[1] + text_h // 2
            
            # Draw white text background for readability
            cv2.rectangle(frame, 
                         (text_x - 8, text_y - text_h - 8),
                         (text_x + text_w + 8, text_y + 8),
                         self.COLOR_TEXT_BG, -1)
            cv2.rectangle(frame, 
                         (text_x - 8, text_y - text_h - 8),
                         (text_x + text_w + 8, text_y + 8),
                         self.COLOR_OBJECT_BOX, 2)
            
            # Draw text (black on white)
            cv2.putText(frame, label, (text_x, text_y),
                       self.font, self.font_scale, self.COLOR_MEASUREMENT, self.thickness)
            
            # Draw center point
            cv2.circle(frame, center, 5, self.COLOR_OBJECT_BOX, -1)


class ObjectMeasurer:
    """Main application class."""
    
    def __init__(self, camera_index: int = 0, resolution: Tuple[int, int] = (1280, 720)):
        self.camera_index = camera_index
        self.resolution = resolution
        
        self.calibrator = CameraCalibrator()
        self.detector = ObjectDetector(self.calibrator)
        self.overlay = MeasurementOverlay()
        
        self.cap = None
        self.fps = 0.0
        self.frame_times = []
    
    def start(self):
        """Initialize and start the camera."""
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)  # DirectShow for Windows
        
        if not self.cap.isOpened():
            # Try without DirectShow
            self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera at index {self.camera_index}")
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        # Disable auto-exposure if possible (for consistent lighting)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual mode
        
        # Camera warmup - quick read to initialize
        print("Warming up camera...")
        for _ in range(15):  # Quick warmup (~0.5 seconds)
            self.cap.read()
        
        print(f"Camera opened: {self.resolution[0]}x{self.resolution[1]}")
        print("Press 'c' to calibrate with A4 paper")
        print("Press 'r' to reset calibration")
        print("Press 'q' to quit")
    
    def update_fps(self):
        """Update FPS calculation."""
        current_time = time.time()
        self.frame_times.append(current_time)
        
        # Keep only last 30 frame times
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
        
        if len(self.frame_times) > 1:
            time_diff = self.frame_times[-1] - self.frame_times[0]
            if time_diff > 0:
                self.fps = (len(self.frame_times) - 1) / time_diff
    
    def run(self):
        """Main application loop."""
        self.start()
        
        window_name = "Object Measurer - Press 'c' to calibrate"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, WINDOW_SIZE[0], WINDOW_SIZE[1])
        
        show_debug = DEBUG_MODE
        preprocessor = ImagePreprocessor()
        
        try:
            while True:
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to read frame")
                    break
                
                self.update_fps()
                
                # Detect and measure objects
                objects = self.detector.detect_objects(frame)
                
                # Draw overlays
                self.overlay.draw_a4_outline(frame, self.calibrator)
                self.overlay.draw_object_measurements(frame, objects)
                self.overlay.draw_status(frame, self.calibrator, self.fps)
                
                # Debug mode: show edge detection and contours
                if show_debug:
                    preprocessed = preprocessor.preprocess(frame)
                    edges = preprocessor.get_edges(preprocessed)
                    
                    # Find and draw contours on debug view
                    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    debug_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                    
                    # Draw top contours in different colors
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
                    for i, cnt in enumerate(contours):
                        color = (0, 255, 0) if i == 0 else (0, 165, 255)  # Green for largest
                        cv2.drawContours(debug_frame, [cnt], -1, color, 2)
                        
                        # Show contour info
                        area = cv2.contourArea(cnt)
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.putText(debug_frame, f"#{i+1} A:{int(area)}", (x, y-5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                    
                    cv2.imshow("Debug: Edges & Contours (press 'd' to hide)", debug_frame)
                
                # Display main frame
                cv2.imshow(window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('c'):
                    print("Attempting calibration...")
                    if self.calibrator.calibrate(frame):
                        print(f"Calibration successful! Pixel ratio: {self.calibrator.calibration.pixels_per_mm:.2f} px/mm")
                    else:
                        print("Calibration failed. Make sure A4 paper is fully visible and flat.")
                        print("TIP: Check the debug window - the A4 paper should appear as a clear rectangle contour.")
                elif key == ord('r'):
                    self.calibrator.reset()
                    print("Calibration reset.")
                elif key == ord('d'):
                    show_debug = not show_debug
                    if not show_debug:
                        cv2.destroyWindow("Debug: Edges & Contours (press 'd' to hide)")
                    print(f"Debug mode: {'ON' if show_debug else 'OFF'}")
        
        finally:
            self.stop()
    
    def stop(self):
        """Release resources."""
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()


def main():
    """Entry point."""
    print("=" * 60)
    print("OBJECT MEASUREMENT SYSTEM")
    print("=" * 60)
    print("\nAccuracy Tips:")
    print("  1. Position camera perpendicular to surface (straight down)")
    print("  2. Use even, diffuse lighting (avoid harsh shadows)")
    print("  3. Use contrasting background (light bg for dark objects)")
    print("  4. Keep A4 paper and objects flat on surface")
    print("  5. Recalibrate when camera position changes")
    print("=" * 60)
    
    try:
        measurer = ObjectMeasurer(camera_index=CAMERA_INDEX, resolution=CAMERA_RESOLUTION)
        measurer.run()
    except RuntimeError as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  - Make sure your webcam is connected")
        print("  - Try changing camera_index to 1 or 2")
        print("  - Check if another application is using the camera")
    except KeyboardInterrupt:
        print("\nInterrupted by user")


if __name__ == "__main__":
    main()
