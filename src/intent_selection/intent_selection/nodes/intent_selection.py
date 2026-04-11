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
6. Supports fullscreen display mode via configuration
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
from intent_selection.config.ros_presets import STD_CFG as ROS_CONFIGS
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
        self.declare_parameter("intention_output_topic", ROS_CONFIGS.topic_intention_output)
        self.declare_parameter("max_messages", ROS_CONFIGS.max_messages)
        
        # Camera configuration
        self.declare_parameter("camera_source", DEFAULT_SELECTION_CONFIG.camera_source)
        self.declare_parameter("camera_device", DEFAULT_SELECTION_CONFIG.camera_device)
        self.declare_parameter("image_width", DEFAULT_SELECTION_CONFIG.image_width)
        self.declare_parameter("image_height", DEFAULT_SELECTION_CONFIG.image_height)
        self.declare_parameter("frame_rate", DEFAULT_SELECTION_CONFIG.frame_rate)
        
        # Display settings
        self.declare_parameter("display_window_name", DEFAULT_SELECTION_CONFIG.window_name)
        self.declare_parameter("display_fullscreen", DEFAULT_SELECTION_CONFIG.display_fullscreen)
        self.declare_parameter("window_width", DEFAULT_SELECTION_CONFIG.window_width)
        self.declare_parameter("window_height", DEFAULT_SELECTION_CONFIG.window_height)
        self.declare_parameter("gaze_proximity_threshold", DEFAULT_SELECTION_CONFIG.gaze_proximity_threshold)
        
        # Get parameter values
        # ROS Topics
        self._camera_topic = self.get_parameter("camera_topic").value
        self._gaze_topic = self.get_parameter("gaze_topic").value
        self._calibration_topic = self.get_parameter("calibration_topic").value
        self._detections_topic = self.get_parameter("detections_topic").value
        self._voice_commands_topic = self.get_parameter("voice_commands_topic").value
        self._vla_input_topic = self.get_parameter("vla_input_topic").value
        self._intention_output_topic = self.get_parameter("intention_output_topic").value
        self._max_messages = self.get_parameter("max_messages").value
        
        # Camera configuration
        self._camera_source = self.get_parameter("camera_source").value
        self._camera_device = self.get_parameter("camera_device").value
        self._image_width = self.get_parameter("image_width").value
        self._image_height = self.get_parameter("image_height").value
        self._frame_rate = self.get_parameter("frame_rate").value
        
        # Display settings
        self._window_name = self.get_parameter("display_window_name").value
        self._fullscreen = self.get_parameter("display_fullscreen").value
        self._window_width = self.get_parameter("window_width").value
        self._window_height = self.get_parameter("window_height").value
        self._proximity_threshold = self.get_parameter("gaze_proximity_threshold").value
        
        # Initialize OpenCV bridge and camera
        self._bridge = CvBridge()
        self._cap = None
        self._window_initialized = False
        
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
        
        # Status tracking
        self._gaze_available = False
        self._detections_available = False
        
        # Valid voice commands from config
        self._eye_gaze_commands = DEFAULT_SELECTION_CONFIG.eye_gaze_commands
        self._general_commands = DEFAULT_SELECTION_CONFIG.general_commands
        
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
        
        # Publisher for general intention commands
        self._intention_pub = self.create_publisher(
            String, self._intention_output_topic, self._max_messages
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
        self.get_logger().info(f"Display Mode: {'Fullscreen' if self._fullscreen else f'Windowed ({self._window_width}x{self._window_height})'}")
        self.get_logger().info(f"Gaze: {self._gaze_topic}")
        self.get_logger().info(f"Detections: {self._detections_topic}")
        self.get_logger().info(f"Voice Commands: {self._voice_commands_topic}")
        self.get_logger().info(f"VLA Output: {self._vla_input_topic}")
        self.get_logger().info(f"Intention Output: {self._intention_output_topic}")
        self.get_logger().info(f"Eye Gaze Commands: {self._eye_gaze_commands}")
        self.get_logger().info(f"General Commands: {self._general_commands}")
    
    def _init_display_window(self):
        """Initialize OpenCV display window with fullscreen or windowed mode."""
        if self._window_initialized:
            return
            
        # Create window
        cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
        
        if self._fullscreen:
            # Set fullscreen mode
            cv2.setWindowProperty(self._window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            self.get_logger().info("Display set to fullscreen mode")
        else:
            # Set windowed mode with specific size
            cv2.resizeWindow(self._window_name, self._window_width, self._window_height)
            cv2.setWindowProperty(self._window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            self.get_logger().info(f"Display set to windowed mode: {self._window_width}x{self._window_height}")
        
        # Add key bindings info
        self.get_logger().info("Key bindings: F - toggle fullscreen, ESC/Q - quit")
        
        self._window_initialized = True
    
    def _toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self._fullscreen = not self._fullscreen
        
        if self._fullscreen:
            cv2.setWindowProperty(self._window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            self.get_logger().info("Switched to fullscreen mode")
        else:
            cv2.setWindowProperty(self._window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self._window_name, self._window_width, self._window_height)
            self.get_logger().info(f"Switched to windowed mode: {self._window_width}x{self._window_height}")
    
    def _handle_keyboard_input(self):
        """Handle keyboard input for display control."""
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('f') or key == ord('F'):
            # Toggle fullscreen
            self._toggle_fullscreen()
        elif key == 27 or key == ord('q') or key == ord('Q'):  # ESC or Q
            # Quit (this will be handled by the main loop)
            self.get_logger().info("Quit key pressed")
            rclpy.shutdown()
    
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
            # self.get_logger().warn("Failed to capture frame from camera device")
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
        self._gaze_available = True
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
        self._detections_available = len(msg.item_list) > 0
        self._update_selected_object()
    
    def _voice_callback(self, msg: String):
        """Process voice commands and trigger intent selection."""
        try:
            # Parse JSON command
            command_data = json.loads(msg.data)
            command = command_data.get("raw", "").lower().strip()
            
            self.get_logger().info(f"Received voice command: {command}")
            
            # Check command type
            is_gaze_command = any(gaze_cmd in command for gaze_cmd in self._eye_gaze_commands)
            is_general_command = any(gen_cmd in command for gen_cmd in self._general_commands)
            
            if is_general_command:
                # Handle general commands that don't require gaze
                self._handle_general_command(command, command_data)
            elif is_gaze_command:
                # Handle gaze-based commands
                self._handle_gaze_command(command, command_data)
            else:
                self.get_logger().warn(f"Unrecognized command: {command}")
                
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Failed to parse voice command JSON: {e}")
        except Exception as e:
            self.get_logger().error(f"Error processing voice command: {e}")
    
    def _handle_general_command(self, command: str, command_data: dict):
        """Handle general commands that don't require eye gaze data."""
        self.get_logger().info(f"Processing general command: {command}")
        
        # Create intention command for general commands
        intention_command = {
            "type": "general_command",
            "command": command,
            "original_data": command_data,
            "timestamp": self.get_clock().now().to_msg().sec
        }
        
        # Publish to intention output topic
        intention_msg = String()
        intention_msg.data = json.dumps(intention_command)
        self._intention_pub.publish(intention_msg)
        
        self.get_logger().info(f"Published general command to intention output: {command}")
    
    def _handle_gaze_command(self, command: str, command_data: dict):
        """Handle commands that require eye gaze data."""
        # Check if we have valid input for target selection
        if not self._gaze_available:
            self.get_logger().warn("Eye gaze command received but no eye gaze data available")
            return
        
        # Determine target coordinates
        target_data = None
        if self._detections_available and self._selected_object_idx >= 0:
            # Use selected object from detections
            selected_object = self._current_detections[self._selected_object_idx]
            target_data = {
                "source": "object_detection",
                "name": selected_object.name,
                "index": selected_object.index,
                "x": selected_object.xywh[0],  # Use x,y for orchestrator compatibility
                "y": selected_object.xywh[1],
                "confidence": selected_object.confidence
            }
            self.get_logger().info(f"Using detected object: {selected_object.name}")
        elif self._current_gaze:
            # Fall back to raw gaze coordinates
            gaze_x, gaze_y = self._current_gaze
            target_data = {
                "source": "raw_gaze",
                "name": "gaze_target",
                "index": -1,
                "x": gaze_x,  # Use x,y for orchestrator compatibility
                "y": gaze_y,
                "confidence": 1.0
            }
            self.get_logger().info(f"Using raw gaze coordinates: ({gaze_x}, {gaze_y})")
        else:
            self.get_logger().warn("No valid target available (no gaze or detections)")
            return
        
        # Create intention command - publish to orchestrator
        intention_command = {
            "type": "gaze_command",
            "command": command,
            "target": target_data,
            "original_data": command_data,
            "timestamp": self.get_clock().now().to_msg().sec
        }
        
        # Publish to intention output topic (orchestrator will handle VLA)
        intention_msg = String()
        intention_msg.data = json.dumps(intention_command)
        self._intention_pub.publish(intention_msg)
        
        self.get_logger().info(f"Published targeted command to orchestrator: {target_data['name']} at ({target_data['x']}, {target_data['y']})")
    
    def _update_selected_object(self):
        """Update which object is currently selected by gaze."""
        if not self._gaze_available or not self._current_gaze:
            self._selected_object_idx = -1
            return
        
        # If no detections available, no object selection possible
        if not self._detections_available or not self._current_detections:
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
        
        # Initialize display window if needed
        if not self._window_initialized:
            self._init_display_window()
        
        # Copy frame for drawing
        display_frame = self._current_frame.copy()
        
        # Draw detection bounding boxes
        if self._detections_available and self._current_detections:
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
        if self._gaze_available and self._current_gaze:
            gaze_x, gaze_y = self._current_gaze
            cv2.circle(display_frame, (gaze_x, gaze_y), 10, self._colors['gaze_circle'], -1)
            cv2.circle(display_frame, (gaze_x, gaze_y), 12, self._colors['gaze_circle'], 2)
        
        # Draw calibration points
        for cal_point in self._calibration_points:
            cv2.circle(display_frame, cal_point, 15, self._colors['calibration'], 2)
            cv2.circle(display_frame, cal_point, 5, self._colors['calibration'], -1)
        
        # Draw status indicators in top right
        frame_height, frame_width = display_frame.shape[:2]
        
        # Status messages for missing components
        status_messages = []
        if not self._gaze_available:
            status_messages.append("No eye gaze available")
        if not self._detections_available:
            status_messages.append("No object detection available")
        
        # Draw status messages in top right
        for i, message in enumerate(status_messages):
            text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            x_pos = frame_width - text_size[0] - 10
            y_pos = 30 + i * 25
            
            # Background rectangle for text
            cv2.rectangle(display_frame, 
                         (x_pos - 5, y_pos - text_size[1] - 5), 
                         (x_pos + text_size[0] + 5, y_pos + 5), 
                         (0, 0, 0), -1)
            
            # Text
            cv2.putText(display_frame, message, (x_pos, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Add status text in bottom left
        status_lines = []
        if self._detections_available and self._selected_object_idx >= 0 and self._current_detections:
            selected_obj = self._current_detections[self._selected_object_idx]
            status_lines.append(f"Selected: {selected_obj.name}")
        elif self._gaze_available:
            status_lines.append("Target: Raw gaze coordinates")
        else:
            status_lines.append("No target selected")
        
        if self._gaze_available:
            status_lines.append(f"Gaze: {self._current_gaze}")
        status_lines.append(f"Objects detected: {len(self._current_detections) if self._current_detections else 0}")
        
        # Add fullscreen indicator
        status_lines.append(f"Display: {'Fullscreen (F to toggle)' if self._fullscreen else 'Windowed (F to toggle)'}")
        
        # Draw status text
        for i, line in enumerate(status_lines):
            y_pos = 30 + i * 25
            cv2.putText(display_frame, line, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, line, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
        
        # Show the frame
        cv2.imshow(self._window_name, display_frame)
        
        # Handle keyboard input
        self._handle_keyboard_input()
    
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