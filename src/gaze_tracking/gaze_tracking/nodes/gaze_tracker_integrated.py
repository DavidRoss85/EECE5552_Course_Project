import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')

import threading
import time
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from eyeGestures.utils import VideoCapture
from eyeGestures import EyeGestures_v2

from gaze_tracking.config.ros2_presets import STD_CFG

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))


class GazeTrackingNode(Node):
    def __init__(self):
        super().__init__('gaze_tracking_node')

        # -- Parameters --
        # 'input_mode': 'device' reads directly from a camera, 'topic' subscribes to a ROS2 image topic
        self.declare_parameter('input_mode', 'device')       # 'device' | 'topic'
        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('env_image_width', 600)
        self.declare_parameter('env_image_height', 500)
        self.declare_parameter('calib_points', 25)
        self.declare_parameter('test_mode', False)           # skip EyeGestures, publish dummy gaze
        self.declare_parameter('show_feed', True)            # display the camera feed in a window
        self.declare_parameter('show_fullscreen', False)     # display feed as fullscreen window
        self.declare_parameter('mirror_x', True)             # flip x coords for non-mirrored cameras
        self.declare_parameter('use_calib_map', False)       # use custom calibration map vs EyeGestures default

        self._env_w      = self.get_parameter('env_image_width').value
        self._env_h      = self.get_parameter('env_image_height').value
        self._calib_pts  = self.get_parameter('calib_points').value
        self._show_feed      = self.get_parameter('show_feed').value
        self._show_fullscreen = self.get_parameter('show_fullscreen').value
        self._mirror_x       = self.get_parameter('mirror_x').value
        self._use_calib_map  = self.get_parameter('use_calib_map').value
        self._input_mode = self.get_parameter('input_mode').value
        self._cam_device = self.get_parameter('camera_device').value
        self._ros_config = STD_CFG

        # -- Publishers --
        self._gaze_pub  = self.create_publisher(Point, self._ros_config.topic_eye_gaze, self._ros_config.max_messages)
        self._calib_pub = self.create_publisher(Point, self._ros_config.topic_eye_gaze_calibration, self._ros_config.max_messages)

        # -- Shared state with tracker thread --
        self._lock         = threading.Lock()
        self._gaze_x       = self._env_w // 2
        self._gaze_y       = self._env_h // 2
        self._calibrating  = True
        self._calib_cx     = self._env_w // 2
        self._calib_cy     = self._env_h // 2
        self._calib_radius = 30

        # Latest frame from the ROS2 camera topic (used in 'topic' mode)
        self._latest_frame = None
        self._bridge = CvBridge()

        # Window initialised once inside the tracker thread to avoid threading issues
        self._window_ready = False

        self._stop = threading.Event()
        test_mode = self.get_parameter('test_mode').value

        if test_mode:
            self._calibrating = False
            self._thread = threading.Thread(target=self._dummy_loop, daemon=True)
            self.get_logger().info('Gaze tracking node ready (TEST MODE - no webcam)')
        elif self._input_mode == 'topic':
            self.create_subscription(
                Image,
                self._ros_config.topic_eye_camera_rgb,
                self._camera_topic_cb,
                10
            )
            self._thread = threading.Thread(target=self._tracker_loop_topic, daemon=True)
            self.get_logger().info(
                f'Gaze tracking node ready (EyeGestures v2, topic mode: {self._ros_config.topic_eye_camera_rgb})'
            )
        else:
            self._thread = threading.Thread(target=self._tracker_loop_device, daemon=True)
            self.get_logger().info(
                f'Gaze tracking node ready (EyeGestures v2, device mode: {self._cam_device})'
            )

        self._thread.start()
        self.create_timer(1.0 / 30.0, self._publish_cb)

    # ------------------------------------------------------------------
    # Camera topic callback (topic mode only)
    # ------------------------------------------------------------------
    def _camera_topic_cb(self, msg):
        frame_bgr = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        with self._lock:
            self._latest_frame = frame_bgr

    # ------------------------------------------------------------------
    # Dummy loop — sinusoidal gaze for pipeline testing
    # ------------------------------------------------------------------
    def _dummy_loop(self):
        t = 0.0
        cx, cy = self._env_w // 2, self._env_h // 2
        amp_x, amp_y = self._env_w * 0.3, self._env_h * 0.25
        while not self._stop.is_set():
            gx = int(cx + amp_x * math.sin(t * 0.4))
            gy = int(cy + amp_y * math.sin(t * 0.25))
            with self._lock:
                self._gaze_x = gx
                self._gaze_y = gy
                self._calibrating = False
            t += 0.05
            time.sleep(0.033)

    # ------------------------------------------------------------------
    # Tracker loop — direct device mode
    # ------------------------------------------------------------------
    def _tracker_loop_device(self):
        gestures = EyeGestures_v2()
        cap = VideoCapture(self._cam_device)
        self._run_tracker(gestures, frame_source=cap)

    # ------------------------------------------------------------------
    # Tracker loop — ROS2 topic mode
    # ------------------------------------------------------------------
    def _tracker_loop_topic(self):
        gestures = EyeGestures_v2()
        self._run_tracker(gestures, frame_source=None)

    # ------------------------------------------------------------------
    # Draw overlay: gaze dot + calibration target + HUD
    # ------------------------------------------------------------------
    def _draw_overlay(self, frame, gx, gy, calib_x, calib_y, calib_r, is_calibrating, iterator):
        if not self._window_ready:
            cv2.namedWindow('Gaze Tracking Feed', cv2.WINDOW_NORMAL)
            if self._show_fullscreen:
                cv2.setWindowProperty('Gaze Tracking Feed', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            self._window_ready = True

        # Flip x coords for non-mirrored cameras
        if self._mirror_x:
            gx      = self._env_w - gx
            calib_x = self._env_w - calib_x

        dot_r   = 10
        overlay = frame.copy()

        if is_calibrating:
            cv2.circle(overlay, (calib_x, calib_y), dot_r * 5, (0, 0, 255), -1)

        cv2.circle(overlay, (gx, gy), dot_r, (255, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # -- HUD text --
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness  = 2
        line_h     = 28
        tx, ty     = 10, 30

        status_text  = 'CALIBRATING' if is_calibrating else 'TRACKING'
        status_color = (0, 140, 255) if is_calibrating else (0, 220, 0)

        lines = [
            (f'Status : {status_text}',                  status_color),
            (f'Gaze   : ({gx}, {gy})',                   (255, 255, 255)),
            (f'Calib  : ({calib_x}, {calib_y})',         (200, 200, 200)),
            (f'Points : {iterator} / {self._calib_pts}', (200, 200, 200)),
        ]

        for i, (text, color) in enumerate(lines):
            y = ty + i * line_h
            cv2.putText(frame, text, (tx + 1, y + 1), font, font_scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
            cv2.putText(frame, text, (tx, y),          font, font_scale, color,     thickness,     cv2.LINE_AA)

        cv2.imshow('Gaze Tracking Feed', frame)
        cv2.waitKey(1)

    # ------------------------------------------------------------------
    # Shared tracker logic
    # ------------------------------------------------------------------
    def _run_tracker(self, gestures, frame_source):
        x = np.arange(0.05, 0.96, 0.1)
        y = np.arange(0.05, 0.96, 0.1)
        xx, yy = np.meshgrid(x, y)
        cal_map = np.column_stack([xx.ravel(), yy.ravel()])
        np.random.shuffle(cal_map)
        if self._use_calib_map:
            gestures.uploadCalibrationMap(cal_map, context='vg_ctx')
        gestures.setClassicalImpact(2)
        gestures.setFixation(1.0)

        iterator = 0
        prev_pt  = (0, 0)

        while not self._stop.is_set():
            # Get frame
            if frame_source is not None:
                ret, frame = frame_source.read()
                if not ret:
                    continue
            else:
                with self._lock:
                    frame = self._latest_frame
                if frame is None:
                    time.sleep(0.005)
                    continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (self._env_w, self._env_h))

            calibrate = iterator < self._calib_pts
            try:
                event, calibration = gestures.step(
                    frame_rgb, calibrate, self._env_w, self._env_h, context='vg_ctx')
            except Exception as e:
                print(f'Caught error: {e}')
                continue
            if event is None:
                continue

            with self._lock:
                self._gaze_x = int(event.point[0])
                self._gaze_y = int(event.point[1])
                self._calibrating = calibrate
                if calibrate and calibration is not None:
                    cx, cy = calibration.point
                    self._calib_cx = int(cx)
                    self._calib_cy = int(cy)
                    self._calib_radius = int(calibration.acceptance_radius)
                    if (cx, cy) != prev_pt:
                        iterator += 1
                        prev_pt = (cx, cy)

                gx, gy           = self._gaze_x, self._gaze_y
                calib_x, calib_y = self._calib_cx, self._calib_cy
                calib_r          = self._calib_radius
                is_calibrating   = self._calibrating

            if self._show_feed:
                self._draw_overlay(frame, gx, gy, calib_x, calib_y, calib_r, is_calibrating, iterator)

        if self._show_feed:
            cv2.destroyAllWindows()

    # ------------------------------------------------------------------
    # Publish callback
    # ------------------------------------------------------------------
    def _publish_cb(self):
        with self._lock:
            gx, gy = self._gaze_x, self._gaze_y
            calibrating = self._calibrating
            cx, cy, cr  = self._calib_cx, self._calib_cy, self._calib_radius

        self._gaze_pub.publish(Point(x=float(gx), y=float(gy), z=0.0))
        # z >= 0 means calibrating (z = acceptance_radius); z = -1 means done
        self._calib_pub.publish(
            Point(x=float(cx), y=float(cy), z=float(cr) if calibrating else -1.0))

    def destroy_node(self):
        self._stop.set()
        if self._show_feed:
            cv2.destroyAllWindows()
        super().destroy_node()


def main():
    rclpy.init()
    node = GazeTrackingNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()