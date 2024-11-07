# realsense_camera.py
import pyrealsense2 as rs
import numpy as np
import cv2
import time
from ultralytics import YOLO

class RealsenseCamera:
    def __init__(self):
        self.pipeline = None
        self.clicked_point = None
        # Load YOLO model
        try:
            self.model = YOLO('yolov8n.pt')
            print("YOLO model loaded successfully")
        except Exception as e:
            print(f"Error loading YOLO model: {str(e)}")
            self.model = None
        self.init_camera()

    def init_camera(self):
        try:
            # Clear any existing pipeline
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except:
                    pass
                self.pipeline = None
            
            # Initialize pipeline
            self.pipeline = rs.pipeline()
            config = rs.config()
            
            # Get device
            ctx = rs.context()
            devices = ctx.query_devices()
            if len(devices) == 0:
                raise RuntimeError("No RealSense devices found")
                
            device = devices[0]
            print(f"Found device: {device.get_info(rs.camera_info.name)}")
            
            # Configure streams
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            
            # Start streaming
            print("Starting pipeline...")
            pipeline_profile = self.pipeline.start(config)
            
            # Get depth scale
            depth_sensor = pipeline_profile.get_device().first_depth_sensor()
            self.depth_scale = depth_sensor.get_depth_scale()
            print(f"Depth scale: {self.depth_scale}")

            # Create align object
            align_to = rs.stream.color
            self.align = rs.align(align_to)
            
            print("Pipeline started successfully")
            time.sleep(2)
            
        except Exception as e:
            print(f"Error initializing camera: {str(e)}")
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except:
                    pass
                self.pipeline = None
            raise

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_point = (x, y)

    def get_distance(self, depth_frame, point):
        return depth_frame[point[1], point[0]] * self.depth_scale

    def draw_distance_info(self, image, point, distance):
        cv2.circle(image, point, 4, (0, 0, 255), -1)
        text = f"Distance: {distance:.2f}m"
        cv2.putText(image, text, (point[0] + 10, point[1]), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    def process_detections(self, color_image, depth_frame, results):
        annotated_frame = color_image.copy()
        
        if results and len(results) > 0:
            for r in results[0].boxes.data:
                x1, y1, x2, y2, conf, cls = r
                x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                
                # Calculate center point
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Get distance for center point
                distance = self.get_distance(depth_frame, (center_x, center_y))
                
                # Draw bounding box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw class label and distance
                label = f"{self.model.names[int(cls)]} {conf:.2f} {distance:.2f}m"
                cv2.putText(annotated_frame, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
        return annotated_frame

    def get_frame_stream(self):
        if not self.pipeline:
            return False, None, None
            
        try:
            # Get frameset of depth and color
            frames = self.pipeline.wait_for_frames(timeout_ms=5000)
            
            # Align frames
            aligned_frames = self.align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                return False, None, None
                
            # Convert images to numpy arrays
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            # Run YOLO detection
            if self.model:
                results = self.model(color_image)
                color_image = self.process_detections(color_image, depth_image, results)
            
            return True, color_image, depth_image
            
        except Exception as e:
            print(f"Error getting frames: {str(e)}")
            return False, None, None

    def release(self):
        if self.pipeline:
            try:
                self.pipeline.stop()
            except:
                pass
            self.pipeline = None