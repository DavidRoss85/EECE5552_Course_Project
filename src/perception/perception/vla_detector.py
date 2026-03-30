"""
Standalone detection node for testing.
Opens a camera, runs HSV color detection, and publishes directly to:
  /vla/coords   — Float32MultiArray [cx, cy] of the largest detected object
  /vla/target   — String color name (red / blue / yellow)
  /vla/preview  — sensor_msgs/Image annotated frame (always published)

Run:
  ros2 run perception vla_detector
  ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video4
  ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video4 -p display:=true
  ros2 run perception vla_detector --ros-args -p camera_source:=topic -p camera_topic:=/input/camera_feed/rgb/full_view
  ros2 run perception vla_detector --ros-args -p colors:='["red"]'
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray, String
from cv_bridge import CvBridge

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

HSV_RANGES = {
    'red':    [((0,   100,  50), (25,  255, 255)),
               ((155, 100,  50), (180, 255, 255))],
    'blue':   [((100, 100, 100), (130, 255, 255))],
    'yellow': [((20,  100, 100), (35,  255, 255))],
}

MIN_AREA = 150
_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
BGR = {'red': (0, 0, 255), 'blue': (255, 80, 0), 'yellow': (0, 220, 255)}


class VlaDetector(Node):
    def __init__(self):
        super().__init__('vla_detector')

        self.declare_parameter('camera_source', 'usb')
        self.declare_parameter('camera_topic', '/input/camera_feed/rgb/full_view')
        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('image_width', 1280)
        self.declare_parameter('image_height', 720)
        self.declare_parameter('colors', ['red', 'blue', 'yellow'])
        self.declare_parameter('display', False)

        self._bridge = CvBridge()
        self._cap = None
        self._display = self.get_parameter('display').value

        self._coords_pub = self.create_publisher(Float32MultiArray, '/vla/coords', 10)
        self._target_pub = self.create_publisher(String, '/vla/target', 10)
        self._preview_pub = self.create_publisher(Image, '/vla/preview', 10)

        requested = self.get_parameter('colors').value
        self._active_colors = {c: v for c, v in HSV_RANGES.items() if c in requested}
        if not self._active_colors:
            self.get_logger().warn(f'No valid colors in {requested}, falling back to all')
            self._active_colors = HSV_RANGES
        self.get_logger().info(f'Detecting: {list(self._active_colors.keys())}')
        self.get_logger().info(f'Display: {"on" if self._display else "off"} | Preview topic: /vla/preview')

        source = self.get_parameter('camera_source').value

        if source == 'usb':
            device = self.get_parameter('camera_device').value
            try:
                cam_arg = int(device)
            except (ValueError, TypeError):
                cam_arg = device
            self._cap = cv2.VideoCapture(cam_arg, cv2.CAP_V4L2)
            w = self.get_parameter('image_width').value
            h = self.get_parameter('image_height').value
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            self.create_timer(1.0 / 30.0, self._usb_cb)
            self.get_logger().info(f'VLA detector: USB camera {cam_arg}')
        else:
            topic = self.get_parameter('camera_topic').value
            self.create_subscription(Image, topic, self._topic_cb, 10)
            self.get_logger().info(f'VLA detector: ROS topic {topic}')

    def _topic_cb(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self._detect(frame)

    def _usb_cb(self):
        if self._cap is None or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        self._detect(frame)

    def _detect(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        best = None
        all_dets = []

        for color_name, ranges in self._active_colors.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lo, hi in ranges:
                mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _KERNEL)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _KERNEL)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < MIN_AREA:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                cx, cy = x + w // 2, y + h // 2
                all_dets.append((area, cx, cy, color_name, (x, y, w, h)))
                if best is None or area > best[0]:
                    best = (area, cx, cy, color_name, (x, y, w, h))

        # always build annotated frame for preview topic
        annotated = frame.copy()
        for area, cx, cy, name, (x, y, w, h) in all_dets:
            color = BGR.get(name, (255, 255, 255))
            is_best = best is not None and (cx, cy, name) == (best[1], best[2], best[3])
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3 if is_best else 1)
            cv2.circle(annotated, (cx, cy), 5, color, -1)
            cv2.putText(annotated, f'{name} ({cx},{cy})', (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        if best is not None:
            _, cx, cy, name, _ = best
            cv2.putText(annotated, f'TARGET: {name}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, BGR.get(name, (255, 255, 255)), 2)

        # publish annotated frame regardless of display setting
        self._preview_pub.publish(self._bridge.cv2_to_imgmsg(annotated, encoding='bgr8'))

        if self._display:
            cv2.imshow('VLA Detector', annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                raise SystemExit

        if best is None:
            return

        _, cx, cy, name, _ = best

        coords = Float32MultiArray()
        coords.data = [float(cx), float(cy)]
        self._coords_pub.publish(coords)

        label = String()
        label.data = name
        self._target_pub.publish(label)

        self.get_logger().info(f'{name} @ ({cx}, {cy})')


def main():
    rclpy.init()
    node = VlaDetector()
    try:
        rclpy.spin(node)
    finally:
        if node._cap is not None:
            node._cap.release()
        cv2.destroyAllWindows()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
