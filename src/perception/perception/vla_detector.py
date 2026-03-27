"""
Standalone detection node for testing.
Opens a camera, runs HSV color detection, and publishes directly to:
  /vla/coords  — Float32MultiArray [cx, cy] of the largest detected object
  /vla/target  — String color name (red / blue / yellow)

Run:
  ros2 run perception vla_detector
  ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video0
  ros2 run perception vla_detector --ros-args -p camera_source:=topic -p camera_topic:=/input/camera_feed/rgb/full_view
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray, Header, String
from cv_bridge import CvBridge

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

HSV_RANGES = {
    'red':    [((0,   100, 100), (10,  255, 255)),
               ((170, 100, 100), (180, 255, 255))],
    'blue':   [((100, 100, 100), (130, 255, 255))],
    'yellow': [((20,  100, 100), (35,  255, 255))],
}

MIN_AREA = 200
_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))


class VlaDetector(Node):
    def __init__(self):
        super().__init__('vla_detector')

        self.declare_parameter('camera_source', 'usb')
        self.declare_parameter('camera_topic', '/input/camera_feed/rgb/full_view')
        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('image_width', 1280)
        self.declare_parameter('image_height', 720)

        self._bridge = CvBridge()
        self._cap = None

        self._coords_pub = self.create_publisher(Float32MultiArray, '/vla/coords', 10)
        self._target_pub = self.create_publisher(String, '/vla/target', 10)

        source = self.get_parameter('camera_source').value

        if source == 'usb':
            device = self.get_parameter('camera_device').value
            try:
                cam_arg = int(device)
            except (ValueError, TypeError):
                cam_arg = device
            self._cap = cv2.VideoCapture(cam_arg)
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
        best = None   # (area, cx, cy, name, bbox)
        all_dets = [] # (cx, cy, name, bbox) for display

        BGR = {'red': (0, 0, 255), 'blue': (255, 80, 0), 'yellow': (0, 220, 255)}

        for color_name, ranges in HSV_RANGES.items():
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

        # draw all detections
        display = frame.copy()
        for area, cx, cy, name, (x, y, w, h) in all_dets:
            color = BGR.get(name, (255, 255, 255))
            is_best = best is not None and (cx, cy, name) == (best[1], best[2], best[3])
            thickness = 3 if is_best else 1
            cv2.rectangle(display, (x, y), (x + w, y + h), color, thickness)
            cv2.circle(display, (cx, cy), 5, color, -1)
            label_text = f'{name} ({cx},{cy})'
            cv2.putText(display, label_text, (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        if best is not None:
            _, cx, cy, name, _ = best
            cv2.putText(display, f'TARGET: {name}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, BGR.get(name, (255, 255, 255)), 2)

        cv2.imshow('VLA Detector', display)
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
