# camera_viewer.py
import cv2
from realsense_camera import RealsenseCamera
import time
import numpy as np

def main():
    rs = None
    try:
        print("\nStarting camera initialization...")
        # Try to initialize camera a few times if needed
        for i in range(3):
            try:
                if rs:
                    rs.release()
                    time.sleep(2)
                rs = RealsenseCamera()
                # Test if we can get a frame
                ret, _, _ = rs.get_frame_stream()
                if ret:
                    print("Camera initialized successfully!")
                    break
            except Exception as e:
                print(f"Attempt {i+1} failed: {str(e)}")
                if i == 2:  # Last attempt
                    print("Failed to initialize camera after 3 attempts")
                    return
                time.sleep(2)
        
        # Create windows and set mouse callback
        cv2.namedWindow('Color Frame')
        cv2.setMouseCallback('Color Frame', rs.mouse_callback)
        
        print("\nStarting frame capture...")
        print("Click on the color image to measure distance at that point")
        print("Press 'q' to quit")
        
        while True:
            ret, color_frame, depth_frame = rs.get_frame_stream()
            
            if not ret:
                print("Failed to get frame, retrying...")
                time.sleep(0.5)
                continue
            
            # Handle clicked point
            if rs.clicked_point:
                distance = rs.get_distance(depth_frame, rs.clicked_point)
                rs.draw_distance_info(color_frame, rs.clicked_point, distance)
            
            # Convert depth to colormap
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_frame, alpha=0.03), 
                cv2.COLORMAP_JET
            )
            
            # Show frames
            cv2.imshow("Color Frame", color_frame)
            cv2.imshow("Depth Frame", depth_colormap)
            
            # Break loop with 'q'
            if cv2.waitKey(50) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError in main loop: {str(e)}")
    finally:
        print("\nCleaning up...")
        if rs:
            rs.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()