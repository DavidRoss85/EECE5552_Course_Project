import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

from robot_interfaces.msg import DetectedList
from gaze_tracking.gaze_utils import DwellSelectionSystem

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

CONFIRM_PHRASES = {'select', 'grab', 'yes', 'confirm', 'take'}


class GazeOverlayNode(Node):
    def __init__(self):
        super().__init__('gaze_overlay_node')

        self.declare_parameter('dwell_threshold', 1.5)
        self.declare_parameter('rgb_topic', '/input/camera_feed/rgb/full_view')

        dwell_thresh = self.get_parameter('dwell_threshold').value
        rgb_topic = self.get_parameter('rgb_topic').value

        self._bridge = CvBridge()
        self._dwell = DwellSelectionSystem(dwell_threshold=dwell_thresh)
        self._current_detections = []
        self._gaze_point = None
        self._latest_frame = None
        self._calibrating = True
        self._calib_cx = 0
        self._calib_cy = 0
        self._calib_radius = 30

        self._selected_pub = self.create_publisher(
            Point, '/gaze_tracking/selected_point', 10)

        self.create_subscription(Image, rgb_topic, self._image_cb, 10)
        self.create_subscription(
            DetectedList, '/intent_selection/detections', self._detections_cb, 10)
        self.create_subscription(
            Point, '/input/eye_gaze/coords', self._gaze_cb, 10)
        self.create_subscription(
            String, '/intent_selection/text_commands', self._voice_cb, 10)
        self.create_subscription(
            Point, '/gaze_tracking/calibration_point', self._calib_cb, 10)

        self.get_logger().info('Gaze overlay node ready')

    def _image_cb(self, msg: Image):
        self._latest_frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def _detections_cb(self, msg: DetectedList):
        self._current_detections = msg.item_list
        self._dwell.targets = []
        for item in self._current_detections:
            if len(item.xyxy) < 4:
                continue
            x1, y1, x2, y2 = item.xyxy[0], item.xyxy[1], item.xyxy[2], item.xyxy[3]
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            radius = int(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 2)
            self._dwell.add_target(center, max(radius, 20), item.name)

    def _gaze_cb(self, msg: Point):
        self._gaze_point = (int(msg.x), int(msg.y))

    def _calib_cb(self, msg: Point):
        self._calibrating = msg.z >= 0.0
        self._calib_cx = int(msg.x)
        self._calib_cy = int(msg.y)
        self._calib_radius = int(msg.z) if msg.z >= 0 else 30

    def _voice_cb(self, msg: String):
        if msg.data.strip().lower() in CONFIRM_PHRASES:
            self._confirm_current_target()

    def _confirm_current_target(self):
        if self._dwell.current_target is not None:
            cx, cy = self._dwell.current_target.center
            self._publish_selected(cx, cy)
            self._dwell.current_target.selected = True

    def _publish_selected(self, cx, cy):
        msg = Point(x=float(cx), y=float(cy), z=0.0)
        self._selected_pub.publish(msg)
        self.get_logger().info(f'Selected object at pixel ({cx}, {cy})')

    def render(self):
        if self._latest_frame is None:
            return

        frame = self._latest_frame.copy()

        # --- calibration overlay ---
        if self._calibrating:
            dim = frame.copy()
            cv2.rectangle(dim, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
            cv2.addWeighted(dim, 0.5, frame, 0.5, 0, frame)
            pt = (self._calib_cx, self._calib_cy)
            cv2.circle(frame, pt, self._calib_radius + 8, (40, 40, 180), -1)
            cv2.circle(frame, pt, self._calib_radius, (80, 80, 255), -1)
            cv2.circle(frame, pt, 8, (255, 255, 255), -1)
            cv2.putText(frame, 'CALIBRATING - stare at the dot',
                        (frame.shape[1] // 2 - 220, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.imshow('VisionGrip - Gaze Selection', frame)
            return

        # --- normal mode ---
        for item in self._current_detections:
            if len(item.xyxy) < 4:
                continue
            x1, y1, x2, y2 = item.xyxy[0], item.xyxy[1], item.xyxy[2], item.xyxy[3]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
            cv2.putText(frame, f'{item.name} {item.confidence:.2f}',
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        self._dwell.draw_targets(frame)

        if self._gaze_point is not None:
            cv2.circle(frame, self._gaze_point, 20, (0, 255, 0), 3)
            cv2.circle(frame, self._gaze_point, 4, (255, 255, 255), -1)
            selected = self._dwell.update(self._gaze_point)
            if selected:
                self._publish_selected(*selected.center)

        cv2.imshow('VisionGrip - Gaze Selection', frame)


def main():
    rclpy.init()
    node = GazeOverlayNode()

    cv2.namedWindow('VisionGrip - Gaze Selection', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('VisionGrip - Gaze Selection',
                          cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            node.render()
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                node._dwell.targets = []
                node.get_logger().info('Dwell targets reset')
    finally:
        cv2.destroyAllWindows()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
