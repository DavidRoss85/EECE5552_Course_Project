#!/usr/bin/env python3
"""
Intent Selection Tester Node
----------------------------
Generates synthetic test data to simulate a user interacting with the intent selection system.

This node publishes:
1. Sinusoidal eye gaze coordinates that move around the screen
2. Fake object detections with bounding boxes at fixed locations
3. Periodic voice commands (both gaze-based and general commands)

Use this to test the IntentSelectionNode without requiring actual hardware.
"""

import json
import math
import random
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import String, Header
from sensor_msgs.msg import Image
from robot_interfaces.msg import DetectedList, DetectedItem
import numpy as np
import cv2
from cv_bridge import CvBridge

from intent_selection.config.ros_presets import STD_CFG as ROS_CONFIGS


class IntentSelectionTester(Node):
    def __init__(self):
        super().__init__('intent_selection_tester')
        
        self.get_logger().info("Starting Intent Selection Tester Node...")
        
        # Declare parameters
        self.declare_parameter("gaze_topic", ROS_CONFIGS.topic_eye_gaze)
        self.declare_parameter("calibration_topic", ROS_CONFIGS.topic_eye_gaze_calibration)
        self.declare_parameter("detections_topic", ROS_CONFIGS.topic_detections)
        self.declare_parameter("voice_commands_topic", ROS_CONFIGS.topic_text_commands)
        self.declare_parameter("camera_topic", ROS_CONFIGS.topic_full_view_rgb)
        self.declare_parameter("max_messages", ROS_CONFIGS.max_messages)
        
        # Test configuration
        self.declare_parameter("image_width", 1280)
        self.declare_parameter("image_height", 720)
        self.declare_parameter("gaze_speed", 0.5)  # Radians per second for sinusoidal movement
        self.declare_parameter("command_interval", 10.0)  # Seconds between commands
        self.declare_parameter("publish_camera", True)  # Whether to publish synthetic camera feed
        
        # Get parameters
        self._gaze_topic = self.get_parameter("gaze_topic").value
        self._calibration_topic = self.get_parameter("calibration_topic").value
        self._detections_topic = self.get_parameter("detections_topic").value
        self._voice_commands_topic = self.get_parameter("voice_commands_topic").value
        self._camera_topic = self.get_parameter("camera_topic").value
        self._max_messages = self.get_parameter("max_messages").value
        
        self._image_width = self.get_parameter("image_width").value
        self._image_height = self.get_parameter("image_height").value
        self._gaze_speed = self.get_parameter("gaze_speed").value
        self._command_interval = self.get_parameter("command_interval").value
        self._publish_camera = self.get_parameter("publish_camera").value
        
        # Publishers
        self._gaze_pub = self.create_publisher(Point, self._gaze_topic, self._max_messages)
        self._calibration_pub = self.create_publisher(Point, self._calibration_topic, self._max_messages)
        self._detections_pub = self.create_publisher(DetectedList, self._detections_topic, self._max_messages)
        self._voice_pub = self.create_publisher(String, self._voice_commands_topic, self._max_messages)
        
        if self._publish_camera:
            self._camera_pub = self.create_publisher(Image, self._camera_topic, self._max_messages)
            self._bridge = CvBridge()
        
        # State tracking
        self._time_start = self.get_clock().now().nanoseconds / 1e9
        self._last_command_time = 0.0
        self._calibration_mode = False
        self._calibration_start_time = 0.0
        
        # Test objects - fixed positions for consistent testing
        self._test_objects = [
            {"name": "red", "center": (320, 200), "size": (80, 60)},
            {"name": "blue", "center": (640, 360), "size": (100, 80)},
            {"name": "yellow", "center": (960, 500), "size": (90, 70)},
        ]
        
        # Command lists for testing
        self._gaze_commands = ["pick", "grab", "take", "move", "get"]
        self._general_commands = ["stop", "reset", "home", "calibrate", "exit", "go to sleep","exit the program"]
        
        # Timers
        self._gaze_timer = self.create_timer(1.0/30.0, self._publish_gaze)  # 30 Hz
        self._detections_timer = self.create_timer(1.0/10.0, self._publish_detections)  # 10 Hz
        self._command_timer = self.create_timer(1.0, self._check_command_timing)  # 1 Hz
        
        if self._publish_camera:
            self._camera_timer = self.create_timer(1.0/15.0, self._publish_camera_frame)  # 15 Hz
        
        self.get_logger().info("Intent Selection Tester initialized")
        self.get_logger().info(f"Publishing gaze data to: {self._gaze_topic}")
        self.get_logger().info(f"Publishing detections to: {self._detections_topic}")
        self.get_logger().info(f"Publishing commands to: {self._voice_commands_topic}")
        if self._publish_camera:
            self.get_logger().info(f"Publishing camera feed to: {self._camera_topic}")
        self.get_logger().info(f"Command interval: {self._command_interval} seconds")
    
    def _get_current_time(self):
        """Get current time in seconds since node start."""
        return self.get_clock().now().nanoseconds / 1e9 - self._time_start
    
    def _publish_gaze(self):
        """Publish synthetic gaze coordinates that move in interesting patterns."""
        current_time = self._get_current_time()
        
        if self._calibration_mode:
            # During calibration, publish calibration points
            cal_time = current_time - self._calibration_start_time
            if cal_time < 10.0:  # 10 second calibration sequence
                # Publish calibration points at screen corners and center
                cal_points = [
                    (50, 50),           # Top-left
                    (self._image_width - 50, 50),  # Top-right
                    (self._image_width // 2, self._image_height // 2),  # Center
                    (50, self._image_height - 50),  # Bottom-left
                    (self._image_width - 50, self._image_height - 50),  # Bottom-right
                ]
                
                point_idx = int(cal_time * len(cal_points) / 10.0)
                if point_idx < len(cal_points):
                    cal_point = Point()
                    cal_point.x = float(cal_points[point_idx][0])
                    cal_point.y = float(cal_points[point_idx][1])
                    self._calibration_pub.publish(cal_point)
            else:
                self._calibration_mode = False
                self.get_logger().info("Calibration sequence completed")
        
        # Generate sinusoidal gaze pattern that visits different areas
        # Create a figure-8 pattern that passes near the test objects
        center_x = self._image_width // 2
        center_y = self._image_height // 2
        
        # Figure-8 pattern
        t = current_time * self._gaze_speed
        radius_x = self._image_width * 0.3
        radius_y = self._image_height * 0.25
        
        gaze_x = center_x + radius_x * math.sin(t)
        gaze_y = center_y + radius_y * math.sin(2 * t)  # Double frequency for figure-8
        
        # Add some random noise to make it more realistic
        gaze_x += random.gauss(0, 10)
        gaze_y += random.gauss(0, 10)
        
        # Clamp to screen bounds
        gaze_x = max(0, min(self._image_width - 1, gaze_x))
        gaze_y = max(0, min(self._image_height - 1, gaze_y))
        
        # Publish gaze point
        gaze_point = Point()
        gaze_point.x = float(gaze_x)
        gaze_point.y = float(gaze_y)
        self._gaze_pub.publish(gaze_point)
    
    def _publish_detections(self):
        """Publish synthetic object detections at fixed locations."""
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = "camera"
        
        detection_list = DetectedList()
        detection_list.header = header
        
        for i, obj in enumerate(self._test_objects):
            # Add some small random variation to make it realistic
            center_noise_x = random.gauss(0, 3)
            center_noise_y = random.gauss(0, 3)
            size_noise = random.gauss(1.0, 0.05)  # ±5% size variation
            
            center_x = obj["center"][0] + center_noise_x
            center_y = obj["center"][1] + center_noise_y
            width = obj["size"][0] * size_noise
            height = obj["size"][1] * size_noise
            
            # Calculate bounding box
            x1 = int(center_x - width/2)
            y1 = int(center_y - height/2)
            x2 = int(center_x + width/2)
            y2 = int(center_y + height/2)
            
            # Create detection item
            item = DetectedItem()
            item.name = obj["name"]
            item.index = i
            item.xyxy = [x1, y1, x2, y2]
            item.xywh = [int(center_x), int(center_y), int(width), int(height)]
            item.confidence = random.uniform(0.85, 0.98)  # High confidence detections
            
            detection_list.item_list.append(item)
        
        self._detections_pub.publish(detection_list)
    
    def _publish_camera_frame(self):
        """Publish synthetic camera frame with colored rectangles representing objects."""
        # Create blank frame
        frame = np.zeros((self._image_height, self._image_width, 3), dtype=np.uint8)
        frame.fill(50)  # Dark gray background
        
        # Draw test objects
        colors = {
            "red": (0, 0, 255),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255)
        }
        
        for obj in self._test_objects:
            center = obj["center"]
            size = obj["size"]
            color = colors.get(obj["name"], (255, 255, 255))
            
            # Draw filled rectangle
            x1 = int(center[0] - size[0]/2)
            y1 = int(center[1] - size[1]/2)
            x2 = int(center[0] + size[0]/2)
            y2 = int(center[1] + size[1]/2)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
            
            # Add label
            cv2.putText(frame, obj["name"], (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Add grid lines for reference
        for x in range(0, self._image_width, 100):
            cv2.line(frame, (x, 0), (x, self._image_height), (30, 30, 30), 1)
        for y in range(0, self._image_height, 100):
            cv2.line(frame, (0, y), (self._image_width, y), (30, 30, 30), 1)
        
        # Convert to ROS message and publish
        try:
            img_msg = self._bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            img_msg.header.stamp = self.get_clock().now().to_msg()
            img_msg.header.frame_id = "camera"
            self._camera_pub.publish(img_msg)
        except Exception as e:
            self.get_logger().error(f"Failed to publish camera frame: {e}")
    
    def _check_command_timing(self):
        """Check if it's time to publish a voice command."""
        current_time = self._get_current_time()
        
        if current_time - self._last_command_time >= self._command_interval:
            self._publish_voice_command()
            self._last_command_time = current_time
    
    def _publish_voice_command(self):
        """Publish a random voice command."""
        # Randomly choose between gaze command (70%) and general command (30%)
        if random.random() < 0.7:
            command = random.choice(self._gaze_commands)
            command_type = "gaze"
            # Add object specification sometimes
            if random.random() < 0.5:
                obj_name = random.choice([obj["name"] for obj in self._test_objects])
                command = f"{command} the {obj_name} object"
        else:
            command = random.choice(self._general_commands)
            command_type = "general"
            
            # Special handling for calibrate command
            if command == "calibrate":
                self._calibration_mode = True
                self._calibration_start_time = self._get_current_time()
                self.get_logger().info("Starting calibration sequence")
        
        # Create voice command message (matching the format from voice_command node)
        voice_data = {
            "raw": command,
            "parsed_command": command,
            "confidence": random.uniform(0.8, 0.95)
        }
        
        voice_msg = String()
        voice_msg.data = json.dumps(voice_data)
        self._voice_pub.publish(voice_msg)
        
        self.get_logger().info(f"Published {command_type} command: '{command}'")


def main(args=None):
    rclpy.init(args=args)
    
    node = IntentSelectionTester()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()