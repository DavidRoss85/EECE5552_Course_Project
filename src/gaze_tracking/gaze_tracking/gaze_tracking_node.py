import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from gaze_tracking.gaze_utils import GazeDirectionTracker

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))


class GazeTrackingNode(Node):
    def __init__(self):
        super().__init__('gaze_tracking_node')

        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('use_ros_camera', False)
        self.declare_parameter('user_camera_topic', '/input/camera_feed/rgb/eye_camera')
        self.declare_parameter('env_image_width', 1280)
        self.declare_parameter('env_image_height', 720)

        self._tracker = GazeDirectionTracker()
        self._bridge = CvBridge()
        self._env_w = self.get_parameter('env_image_width').value
        self._env_h = self.get_parameter('env_image_height').value

        self._pub = self.create_publisher(Point, '/input/eye_gaze/coords', 10)

        use_ros = self.get_parameter('use_ros_camera').value
        if use_ros:
            topic = self.get_parameter('user_camera_topic').value
            self.create_subscription(Image, topic, self._ros_camera_cb, 10)
            self.get_logger().info(f'Gaze tracker reading from ROS topic: {topic}')
        else:
            device_param = self.get_parameter('camera_device').value
            try:
                device = int(device_param)
            except (ValueError, TypeError):
                device = device_param
            self._cap = cv2.VideoCapture(device)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.create_timer(1.0 / 30.0, self._webcam_cb)
            self.get_logger().info(f'Gaze tracker reading from device: {device}')

    def _process_and_publish(self, frame):
        frame = cv2.flip(frame, 1)
        gaze_dir, _ = self._tracker.process_frame(frame)
        if gaze_dir is None:
            return
        env_shape = (self._env_h, self._env_w, 3)
        gx, gy = self._tracker.project_gaze_to_screen(gaze_dir, frame.shape, env_shape)
        msg = Point(x=float(gx), y=float(gy), z=0.0)
        self._pub.publish(msg)

    def _webcam_cb(self):
        ret, frame = self._cap.read()
        if not ret:
            return
        self._process_and_publish(frame)

    def _ros_camera_cb(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self._process_and_publish(frame)


def main():
    rclpy.init()
    node = GazeTrackingNode()
    try:
        rclpy.spin(node)
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
