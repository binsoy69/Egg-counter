"""
Image Capture Script for Dataset Collection
Press 'c' to capture an image
Press 'q' to quit
"""

import cv2
import os
from datetime import datetime

def create_output_folder(folder_name="captured_images"):
    """Create the output folder if it doesn't exist."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Created folder: {folder_name}")
    return folder_name

def capture_images(camera_index=0, output_folder="captured_images"):
    """
    Capture images from camera with live feed.
    
    Args:
        camera_index: Camera device index (0 for default camera)
        output_folder: Folder to save captured images
    """
    # Create output folder
    folder = create_output_folder(output_folder)
    
    # Initialize camera
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"Error: Could not open camera {camera_index}")
        return
    
    # Set camera resolution (optional - adjust as needed)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n" + "="*50)
    print("IMAGE CAPTURE TOOL")
    print("="*50)
    print("Controls:")
    print("  [C] - Capture image")
    print("  [Q] - Quit")
    print("="*50 + "\n")
    
    image_count = 0
    
    while True:
        # Read frame from camera
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Could not read frame from camera")
            break
        
        # Create a display frame with instructions
        display_frame = frame.copy()
        
        # Add text overlay with instructions and count
        cv2.putText(display_frame, "Press 'C' to capture | 'Q' to quit", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Images captured: {image_count}", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Show the frame
        cv2.imshow("Image Capture - Press 'C' to capture, 'Q' to quit", display_frame)
        
        # Wait for key press (1ms delay for smooth video)
        key = cv2.waitKey(1) & 0xFF
        
        # Capture image when 'c' is pressed
        if key == ord('c') or key == ord('C'):
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"image_{timestamp}.jpg"
            filepath = os.path.join(folder, filename)
            
            # Save the original frame (not the one with overlay)
            cv2.imwrite(filepath, frame)
            image_count += 1
            print(f"[{image_count}] Saved: {filepath}")
            
            # Flash effect to indicate capture
            flash_frame = cv2.addWeighted(frame, 0.5, 
                                          255 * cv2.UMat.ones(frame.shape, dtype=frame.dtype).get() 
                                          if hasattr(cv2.UMat, 'ones') 
                                          else 255 * (frame * 0 + 1), 0.5, 0)
            cv2.imshow("Image Capture - Press 'C' to capture, 'Q' to quit", flash_frame)
            cv2.waitKey(100)  # Brief flash
        
        # Quit when 'q' is pressed
        elif key == ord('q') or key == ord('Q'):
            print(f"\nExiting... Total images captured: {image_count}")
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\nImages saved to: {os.path.abspath(folder)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture images from camera for dataset collection")
    parser.add_argument("--camera", "-c", type=int, default=0, 
                        help="Camera index (default: 0)")
    parser.add_argument("--output", "-o", type=str, default="captured_images",
                        help="Output folder for captured images (default: captured_images)")
    
    args = parser.parse_args()
    
    capture_images(camera_index=args.camera, output_folder=args.output)
