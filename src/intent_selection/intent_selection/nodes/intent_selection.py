#!/usr/bin/env python3
"""
Intent Selection Node
--------------------
Integrates eye gaze, voice commands, and object detection for user intent recognition.

This node:
1. Displays camera feed with eye gaze overlay and detection bounding boxes
2. Highlights objects under gaze with color changes
3. Shows calibration points when needed
4. Captures voice commands and maps them to gazed objects
5. Publishes intent commands to VLA input topic
"""

import json
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from std_msgs.msg import String
from cv_bridge import CvBridge

from robot_interfaces.msg import DetectedList
from intent_selection.config.ros_presets import ROS_CONFIGS
from intent_selection.config.selection_presets import DEFAULT_SELECTION_CONFIG


class IntentSelectionNode(Node):
    def __init__(self):
        super().__init__('intent_selection_node')
        
        self.get_logger().info("Initializing Intent Selection Node...")
        
        # Declare parameters with defaults
        # ROS Topics
        self.declare_parameter("camera_topic", ROS_CONFIGS.topic_full_view_rgb)
        self.declare_parameter("gaze_topic", ROS_CONFIGS.topic_eye_gaze)
        self.declare_parameter("calibration_topic", ROS_CONFIGS.topic_eye_gaze_calibration)
        self.declare_parameter("detections_topic", ROS_CONFIGS.topic_detections)
        self.declare_parameter("voice_commands_topic", ROS_CONFIGS.topic_text_commands)
        self.declare_parameter("vla_input_topic", ROS_CONFIGS.topic_vla_input)
        self.declare_parameter("max_messages", ROS_CONFIGS.max_messages)
        
        # Camera configuration
        self.declare_parameter("camera_source", DEFAULT_SELECTION_CONFIG.camera_source)  # 'topic' or 'device'
        self.declare_parameter("camera_device", DEFAULT_SELECTION_CONFIG.camera_device)  # e.g., '/dev/video0' or 0
        self.declare_parameter("image_width", DEFAULT_SELECTION_CONFIG.image_width)
        self.declare_parameter("image_height", DEFAULT_SELECTION_CONFIG.image_height)
        self.declare_parameter("frame_rate", DEFAULT_SELECTION_CONFIG.frame_rate)
        
        # Interface settings
        self.declare_parameter("display_window_name", DEFAULT_SELECTION_CONFIG.window_name)
        self.declare_parameter("gaze_proximity_threshold", DEFAULT_SELECTION_CONFIG.gaze_proximity_threshold)
        
        # Get parameter values
        # ROS Topics
        self._camera_topic = self.get_parameter("camera_topic").value
        self._gaze_topic = self.get_parameter("gaze_topic").value
        self._calibration_topic = self.get_parameter("calibration_topic").value
        self._detections_topic = self.get_parameter("detections_topic").value
        self._voice_commands_topic = self.get_parameter("voice_commands_topic").value
        self._vla_input_topic = self.get_parameter("vla_input_topic").value
        self._max_messages = self.get_parameter("max_messages").value
        
        # Camera configuration
        self._camera_source = self.get_parameter("camera_source").value
        self._camera_device = self.get_parameter("camera_device").value
        self._image_width = self.get_parameter("image_width").value
        self._image_height = self.get_parameter("image_height").value
        self._frame_rate = self.get_parameter("frame_rate").value
        
        # Interface settings
        self._window_name = self.get_parameter("display_window_name").value
        self._proximity_threshold = self.get_parameter("gaze_proximity_threshold").value
        
        # Initialize OpenCV bridge and camera
        self._bridge = CvBridge()
        self._cap = None
        
        # Initialize camera based on source
        if self._camera_source.lower() == 'device':
            self._init_device_camera()
        else:
            self._init_topic_camera()
        
        # State variables
        self._current_frame = None
        self._current_gaze = None
        self._current_detections = None
        self._calibration_points = []
        self._selected_object_idx = -1  # Index of currently gazed object
        
        # Valid voice commands from config
        self._valid_commands = DEFAULT_SELECTION_CONFIG.text_commands
        
        # Colors for visualization (BGR format)
        self._colors = {
            'gaze_circle': (0, 255, 0),      # Green
            'bbox_normal': (255, 0, 0),      # Blue
            'bbox_selected': (0, 255, 255),  # Yellow
            'calibration': (0, 0, 255)       # Red
        }
        
        # Subscribers (camera subscription handled by init methods)
        self._gaze_sub = self.create_subscription(
            Point, self._gaze_topic, self._gaze_callback, self._max_messages
        )
        
        self._calibration_sub = self.create_subscription(
            Point, self._calibration_topic, self._calibration_callback, self._max_messages
        )
        
        self._detections_sub = self.create_subscription(
            DetectedList, self._detections_topic, self._detections_callback, self._max_messages
        )
        
        self._voice_sub = self.create_subscription(
            String, self._voice_commands_topic, self._voice_callback, self._max_messages
        )
        
        # Publisher for VLA commands
        self._vla_pub = self.create_publisher(
            String, self._vla_input_topic, self._max_messages
        )
        
        # Timer for display updates and device camera capture
        if self._camera_source.lower() == 'device':
            self._camera_timer = self.create_timer(1.0/self._frame_rate, self._capture_device_frame)
        self._display_timer = self.create_timer(1.0/30.0, self._update_display)
        
        self.get_logger().info(f"Intent Selection Node initialized")
        self.get_logger().info(f"Camera Source: {self._camera_source}")
        if self._camera_source.lower() == 'topic':
            self.get_logger().info(f"Camera Topic: {self._camera_topic}")
        else:
            self.get_logger().info(f"Camera Device: {self._camera_device}")
        self.get_logger().info(f"Gaze: {self._gaze_topic}")
        self.get_logger().info(f"Detections: {self._detections_topic}")
        self.get_logger().info(f"Voice Commands: {self._voice_commands_topic}")
        self.get_logger().info(f"VLA Output: {self._vla_input_topic}")
        self.get_logger().info(f"Valid Commands: {self._valid_commands}")
    
    def _init_topic_camera(self):
        """Initialize camera from ROS topic."""
        self._camera_sub = self.create_subscription(
            Image, self._camera_topic, self._camera_callback, self._max_messages
        )
        self.get_logger().info(f"Subscribing to camera topic: {self._camera_topic}")
    
    def _init_device_camera(self):
        """Initialize camera from device."""
        try:
            # Handle both integer and string device paths
            device = self._camera_device
            if isinstance(device, str) and device.isdigit():
                device = int(device)
                
            self._cap = cv2.VideoCapture(device)
            
            if not self._cap.isOpened():
                self.get_logger().error(f"Failed to open camera device: {self._camera_device}")
                raise RuntimeError("Camera device could not be opened")
            
            # Set camera properties
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._image_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._image_height)
            
            self.get_logger().info(f"Camera device {self._camera_device} opened successfully")
            
        except Exception as e:
            self.get_logger().error(f"Failed to initialize camera device: {e}")
            raise
    
    def _capture_device_frame(self):
        """Capture frame from device camera."""
        if self._cap is None or not self._cap.isOpened():
            return
            
        ret, frame = self._cap.read()
        if not ret:
            self.get_logger().warn("Failed to capture frame from camera device")
            return
            
        self._current_frame = frame
    
    def _camera_callback(self, msg: Image):
        """Store the latest camera frame."""
        try:
            self._current_frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"Failed to convert camera image: {e}")
    
    def _gaze_callback(self, msg: Point):
        """Store the latest gaze coordinates."""
        self._current_gaze = (int(msg.x), int(msg.y))
        self._update_selected_object()
    
    def _calibration_callback(self, msg: Point):
        """Store calibration points to display."""
        calibration_point = (int(msg.x), int(msg.y))
        self._calibration_points.append(calibration_point)
        
        # Keep only last 10 calibration points to prevent memory buildup
        if len(self._calibration_points) > 10:
            self._calibration_points = self._calibration_points[-10:]
    
    def _detections_callback(self, msg: DetectedList):
        """Store the latest object detections."""
        self._current_detections = msg.item_list
        self._update_selected_object()
    
    def _voice_callback(self, msg: String):
        """Process voice commands and trigger intent selection."""
        try:
            # Parse JSON command
            command_data = json.loads(msg.data)
            command = command_data.get("raw", "").lower().strip()
            
            self.get_logger().info(f"Received voice command: {command}")
            
            # Check if command is valid
            is_valid_command = any(valid_cmd in command for valid_cmd in self._valid_commands)
            
            if not is_valid_command:
                self.get_logger().warn(f"Invalid command received: {command}")
                return
            
            # Check if we have a selected object
            if self._selected_object_idx < 0 or not self._current_detections:
                self.get_logger().warn("No object currently selected by gaze")
                return
            
            # Get the selected object
            selected_object = self._current_detections[self._selected_object_idx]
            
            # Create VLA command
            vla_command = {
                "command": command,
                "target_object": {
                    "name": selected_object.name,
                    "index": selected_object.index,
                    "center_x": selected_object.xywh[0],
                    "center_y": selected_object.xywh[1],
                    "confidence": selected_object.confidence
                },
                "timestamp": self.get_clock().now().to_msg().sec
            }
            
            # Publish to VLA
            vla_msg = String()
            vla_msg.data = json.dumps(vla_command)
            self._vla_pub.publish(vla_msg)
            
            self.get_logger().info(f"Published VLA command: {selected_object.name} at ({selected_object.xywh[0]}, {selected_object.xywh[1]})")
            
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Failed to parse voice command JSON: {e}")
        except Exception as e:
            self.get_logger().error(f"Error processing voice command: {e}")
    
    def _update_selected_object(self):
        """Update which object is currently selected by gaze."""
        if not self._current_gaze or not self._current_detections:
            self._selected_object_idx = -1
            return
        
        gaze_x, gaze_y = self._current_gaze
        min_distance = float('inf')
        selected_idx = -1
        
        for idx, detection in enumerate(self._current_detections):
            # Get center of bounding box from xywh format
            center_x, center_y = detection.xywh[0], detection.xywh[1]
            
            # Calculate distance from gaze to object center
            distance = np.sqrt((gaze_x - center_x)**2 + (gaze_y - center_y)**2)
            
            if distance < min_distance and distance < self._proximity_threshold:
                min_distance = distance
                selected_idx = idx
        
        self._selected_object_idx = selected_idx
    
    def _update_display(self):
        """Update the display window with overlays."""
        if self._current_frame is None:
            return
        
        # Copy frame for drawing
        display_frame = self._current_frame.copy()
        
        # Draw detection bounding boxes
        if self._current_detections:
            for idx, detection in enumerate(self._current_detections):
                # Get bounding box from xyxy format
                x1, y1, x2, y2 = detection.xyxy[:4]
                
                # Choose color based on selection
                color = self._colors['bbox_selected'] if idx == self._selected_object_idx else self._colors['bbox_normal']
                thickness = 3 if idx == self._selected_object_idx else 2
                
                # Draw rectangle
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, thickness)
                
                # Draw label
                label = f"{detection.name} ({detection.confidence:.2f})"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(display_frame, (x1, y1 - label_size[1] - 10), 
                            (x1 + label_size[0], y1), color, -1)
                cv2.putText(display_frame, label, (x1, y1 - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw gaze circle
        if self._current_gaze:
            gaze_x, gaze_y = self._current_gaze
            cv2.circle(display_frame, (gaze_x, gaze_y), 10, self._colors['gaze_circle'], -1)
            cv2.circle(display_frame, (gaze_x, gaze_y), 12, self._colors['gaze_circle'], 2)
        
        # Draw calibration points
        for cal_point in self._calibration_points:
            cv2.circle(display_frame, cal_point, 15, self._colors['calibration'], 2)
            cv2.circle(display_frame, cal_point, 5, self._colors['calibration'], -1)
        
        # Add status text
        status_lines = []
        if self._selected_object_idx >= 0 and self._current_detections:
            selected_obj = self._current_detections[self._selected_object_idx]
            status_lines.append(f"Selected: {selected_obj.name}")
        else:
            status_lines.append("No object selected")
        
        status_lines.append(f"Gaze: {self._current_gaze if self._current_gaze else 'None'}")
        status_lines.append(f"Objects detected: {len(self._current_detections) if self._current_detections else 0}")
        
        # Draw status text
        for i, line in enumerate(status_lines):
            y_pos = 30 + i * 25
            cv2.putText(display_frame, line, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, line, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        # Show the frame
        cv2.imshow(self._window_name, display_frame)
        cv2.waitKey(1)
    
    def destroy_node(self):
        """Clean up resources."""
        if self._cap is not None:
            self._cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    node = IntentSelectionNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()