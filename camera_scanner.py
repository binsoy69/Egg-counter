"""
Camera Diagnostic Tool
Scans for available cameras and shows which ones work.
"""
import cv2
import time

def scan_cameras(max_index=5):
    """Scan for available cameras and test each one."""
    print("Scanning for available cameras...\n")
    
    working_cameras = []
    
    for i in range(max_index):
        print(f"Testing camera index {i}...", end=" ")
        
        # Try DirectShow first (Windows)
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            cap = cv2.VideoCapture(i)
        
        if cap.isOpened():
            # Try to read a frame
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Warmup
            for _ in range(30):
                cap.read()
                time.sleep(0.033)
            
            ret, frame = cap.read()
            
            if ret and frame is not None:
                # Check if frame is not just black
                mean_brightness = frame.mean()
                if mean_brightness > 5:  # Not completely black
                    print(f"OK - Working (brightness: {mean_brightness:.1f})")
                    working_cameras.append((i, "working", mean_brightness))
                else:
                    print(f"BLACK SCREEN (brightness: {mean_brightness:.1f})")
                    working_cameras.append((i, "black", mean_brightness))
            else:
                print("CANNOT READ FRAME")
            
            cap.release()
        else:
            print("NOT AVAILABLE")
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    
    if working_cameras:
        for idx, status, brightness in working_cameras:
            if status == "working":
                print(f"  Camera {idx}: ✓ WORKING (use CAMERA_INDEX = {idx})")
            else:
                print(f"  Camera {idx}: ✗ Black screen")
    else:
        print("  No cameras detected!")
    
    # Show a preview of working cameras
    print("\n" + "=" * 50)
    print("Press any key to close each preview window...")
    print("=" * 50)
    
    for idx, status, _ in working_cameras:
        if status == "working":
            print(f"\nShowing preview for camera {idx}...")
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            
            if cap.isOpened():
                # Warmup
                for _ in range(30):
                    cap.read()
                
                ret, frame = cap.read()
                if ret:
                    cv2.imshow(f"Camera {idx} Preview", frame)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                cap.release()

if __name__ == "__main__":
    scan_cameras()
