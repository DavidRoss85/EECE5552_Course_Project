import threading
import time
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))


class GazeTrackingNode(Node):
    def __init__(self):
        super().__init__('gaze_tracking_node')

        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('env_image_width', 1280)
        self.declare_parameter('env_image_height', 720)
        self.declare_parameter('calib_points', 50)
        self.declare_parameter('test_mode', False)  # skip EyeGestures, publish dummy gaze

        self._env_w = self.get_parameter('env_image_width').value
        self._env_h = self.get_parameter('env_image_height').value
        self._calib_pts = self.get_parameter('calib_points').value

        cam_param = self.get_parameter('camera_device').value
        try:
            self._cam_index = int(cam_param)
        except (ValueError, TypeError):
            self._cam_index = 0

        self._gaze_pub = self.create_publisher(Point, '/input/eye_gaze/coords', 10)
        self._calib_pub = self.create_publisher(Point, '/gaze_tracking/calibration_point', 10)

        # Shared state with tracker thread
        self._lock = threading.Lock()
        self._gaze_x = self._env_w // 2
        self._gaze_y = self._env_h // 2
        self._calibrating = True
        self._calib_cx = self._env_w // 2
        self._calib_cy = self._env_h // 2
        self._calib_radius = 30

        self._stop = threading.Event()
        test_mode = self.get_parameter('test_mode').value
        if test_mode:
            self._calibrating = False  # skip calibration immediately
            self._thread = threading.Thread(target=self._dummy_loop, daemon=True)
            self.get_logger().info('Gaze tracking node ready (TEST MODE - no webcam)')
        else:
            self._thread = threading.Thread(target=self._tracker_loop, daemon=True)
            self.get_logger().info('Gaze tracking node ready (EyeGestures v2)')
        self._thread.start()

        self.create_timer(1.0 / 30.0, self._publish_cb)

    def _dummy_loop(self):
        """Publishes a slow sinusoidal gaze for pipeline testing without a webcam."""
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

    def _tracker_loop(self):
        from eyeGestures.utils import VideoCapture
        from eyeGestures import EyeGestures_v2

        gestures = EyeGestures_v2()
        cap = VideoCapture(self._cam_index)

        x = np.arange(0, 1.1, 0.2)
        y = np.arange(0, 1.1, 0.2)
        xx, yy = np.meshgrid(x, y)
        cal_map = np.column_stack([xx.ravel(), yy.ravel()])
        np.random.shuffle(cal_map)
        gestures.uploadCalibrationMap(cal_map, context='vg_ctx')
        gestures.setClassicalImpact(2)
        gestures.setFixation(1.0)

        iterator = 0
        prev_pt = (0, 0)

        while not self._stop.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            calibrate = iterator < self._calib_pts
            try:
                event, calibration = gestures.step(
                    frame_rgb, calibrate, self._env_w, self._env_h, context='vg_ctx')
            except Exception:
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

    def _publish_cb(self):
        with self._lock:
            gx, gy = self._gaze_x, self._gaze_y
            calibrating = self._calibrating
            cx, cy, cr = self._calib_cx, self._calib_cy, self._calib_radius

        self._gaze_pub.publish(Point(x=float(gx), y=float(gy), z=0.0))
        # z >= 0 means calibrating (z = acceptance_radius); z = -1 means done
        self._calib_pub.publish(
            Point(x=float(cx), y=float(cy), z=float(cr) if calibrating else -1.0))

    def destroy_node(self):
        self._stop.set()
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
