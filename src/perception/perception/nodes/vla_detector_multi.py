"""
Multi-color VLA detector.
Detects all configured colors simultaneously and publishes:
  /vla/coords    — Float32MultiArray [cx, cy] of the BEST (largest) detection (model input)
  /vla/target    — String color name of the best detection (model input)
  /vla/detections — DetectedList of ALL detected objects across all colors (UI input)
  /vla/preview   — Image annotated frame

This is a drop-in replacement for vla_detector that also feeds the dwell UI
with all simultaneous targets without breaking the /vla/coords model interface.
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray, String, Header
from cv_bridge import CvBridge
from robot_interfaces.msg import DetectedList, DetectedItem

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

HSV_RANGES = {
    'red':    [((0,   100,  50), (25,  255, 255)),
               ((155, 100,  50), (180, 255, 255))],
    'blue':   [((100, 100, 100), (130, 255, 255))],
    'yellow': [((20,  100, 100), (35,  255, 255))],
}

MIN_AREA = 150
_KERNEL  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
BGR      = {'red': (0, 0, 255), 'blue': (255, 80, 0), 'yellow': (0, 220, 255)}


class VlaDetectorMulti(Node):
    def __init__(self):
        super().__init__('vla_detector_multi')

        self.declare_parameter('camera_source', 'topic')
        self.declare_parameter('camera_topic',  '/cameras/front/image_raw')
        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('image_width',   640)
        self.declare_parameter('image_height',  480)
        self.declare_parameter('colors',        ['red', 'blue', 'yellow'])
        self.declare_parameter('display',       False)

        self._bridge   = CvBridge()
        self._cap      = None
        self._display  = self.get_parameter('display').value

        requested = self.get_parameter('colors').value
        self._active_colors = {c: v for c, v in HSV_RANGES.items() if c in requested}
        if not self._active_colors:
            self.get_logger().warn(f'No valid colors in {requested}, using all')
            self._active_colors = HSV_RANGES

        # ── Publishers ───────────────────────────────────────────────────
        self._coords_pub     = self.create_publisher(Float32MultiArray, '/vla/coords',      10)
        self._target_pub     = self.create_publisher(String,            '/vla/target',      10)
        self._detections_pub = self.create_publisher(DetectedList,      '/vla/detections',  10)
        self._preview_pub    = self.create_publisher(Image,             '/vla/preview',     10)

        source = self.get_parameter('camera_source').value
        if source == 'usb':
            device = self.get_parameter('camera_device').value
            try:    cam_arg = int(device)
            except: cam_arg = device
            self._cap = cv2.VideoCapture(cam_arg, cv2.CAP_V4L2)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.get_parameter('image_width').value)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.get_parameter('image_height').value)
            self.create_timer(1.0 / 30.0, self._usb_cb)
            self.get_logger().info(f'[vla_detector_multi] USB cam {cam_arg}  colors={list(self._active_colors)}')
        else:
            topic = self.get_parameter('camera_topic').value
            self.create_subscription(Image, topic, self._topic_cb, 10)
            self.get_logger().info(f'[vla_detector_multi] topic {topic}  colors={list(self._active_colors)}')

    def _topic_cb(self, msg: Image):
        self._detect(self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8'))

    def _usb_cb(self):
        if self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret: self._detect(frame)

    def _detect(self, frame):
        hsv      = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        all_dets = []   # (area, cx, cy, x, y, w, h, color_name)

        for color_name, ranges in self._active_colors.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lo, hi in ranges:
                mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  _KERNEL)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _KERNEL)

            for cnt in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
                area = cv2.contourArea(cnt)
                if area < MIN_AREA:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                all_dets.append((area, x + w // 2, y + h // 2, x, y, w, h, color_name))

        # ── Annotated preview ─────────────────────────────────────────────
        annotated = frame.copy()
        best = max(all_dets, key=lambda d: d[0]) if all_dets else None

        for area, cx, cy, x, y, w, h, name in all_dets:
            color    = BGR.get(name, (255, 255, 255))
            is_best  = best is not None and (cx, cy, name) == (best[1], best[2], best[7])
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3 if is_best else 1)
            cv2.circle(annotated, (cx, cy), 5, color, -1)
            cv2.putText(annotated, f'{name} ({cx},{cy})', (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        if best:
            cv2.putText(annotated, f'TARGET: {best[7]}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, BGR.get(best[7], (255,255,255)), 2)

        self._preview_pub.publish(self._bridge.cv2_to_imgmsg(annotated, encoding='bgr8'))

        if self._display:
            cv2.imshow('VLA Detector Multi', annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                raise SystemExit

        if not all_dets:
            return

        # ── /vla/coords + /vla/target — best detection (model input) ─────
        _, cx, cy, _, _, _, _, name = best
        coords      = Float32MultiArray(); coords.data = [float(cx), float(cy)]
        label       = String();            label.data  = name
        self._coords_pub.publish(coords)
        self._target_pub.publish(label)

        # ── /vla/detections — all detections (dwell UI) ───────────────────
        det_list       = DetectedList()
        det_list.header = Header()
        det_list.header.stamp = self.get_clock().now().to_msg()

        for i, (area, cx, cy, x, y, w, h, dname) in enumerate(all_dets):
            item            = DetectedItem()
            item.name       = dname
            item.index      = i
            item.xyxy       = [x, y, x + w, y + h]
            item.xywh       = [cx, cy, w, h]
            item.confidence = 1.0
            det_list.item_list.append(item)

        self._detections_pub.publish(det_list)
        self.get_logger().debug(
            f'[vla_detector_multi] {len(all_dets)} detections  best={name}@({cx},{cy})')


def main():
    rclpy.init()
    node = VlaDetectorMulti()
    try:
        rclpy.spin(node)
    finally:
        if node._cap:
            node._cap.release()
        cv2.destroyAllWindows()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
