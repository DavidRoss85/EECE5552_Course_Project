import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from geometry_msgs.msg import Point, PoseStamped
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Header
import tf2_ros
import tf2_geometry_msgs
from cv_bridge import CvBridge

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

GRIPPER_DOWN = (0.0, 0.7071068, 0.0, 0.7071068)


class ObjectLocalizerNode(Node):
    def __init__(self):
        super().__init__('object_localizer_node')

        self.declare_parameter('depth_topic', '/cameras/top/depth')
        self.declare_parameter('camera_info_topic', '/cameras/top/camera_info')
        self.declare_parameter('camera_frame', 'camera_top_optical_frame')

        depth_topic = self.get_parameter('depth_topic').value
        camera_info_topic = self.get_parameter('camera_info_topic').value
        self._camera_frame = self.get_parameter('camera_frame').value

        self._bridge = CvBridge()
        self._intrinsics = None
        self._latest_depth = None

        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        self._goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)

        self.create_subscription(CameraInfo, camera_info_topic, self._info_cb, 10)
        self.create_subscription(Image, depth_topic, self._depth_cb, 10)
        self.create_subscription(
            Point, '/gaze_tracking/selected_point', self._selected_cb, 10)

        self.get_logger().info('Object localizer ready')

    def _info_cb(self, msg: CameraInfo):
        K = msg.k
        self._intrinsics = {
            'fx': K[0], 'fy': K[4], 'cx': K[2], 'cy': K[5]
        }

    def _depth_cb(self, msg: Image):
        self._latest_depth = self._bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')

    def _selected_cb(self, msg: Point):
        if self._intrinsics is None:
            self.get_logger().warn('No camera intrinsics yet, ignoring selection')
            return
        if self._latest_depth is None:
            self.get_logger().warn('No depth image yet, ignoring selection')
            return

        u, v = int(msg.x), int(msg.y)
        h, w = self._latest_depth.shape
        u = np.clip(u, 0, w - 1)
        v = np.clip(v, 0, h - 1)

        depth = float(self._latest_depth[v, u])
        if depth <= 0.0 or np.isnan(depth):
            self.get_logger().warn(f'Invalid depth at ({u},{v}): {depth}')
            return

        fx = self._intrinsics['fx']
        fy = self._intrinsics['fy']
        cx = self._intrinsics['cx']
        cy = self._intrinsics['cy']

        X = (u - cx) * depth / fx
        Y = (v - cy) * depth / fy
        Z = depth

        cam_pose = PoseStamped()
        cam_pose.header.frame_id = self._camera_frame
        cam_pose.header.stamp = self.get_clock().now().to_msg()
        cam_pose.pose.position.x = X
        cam_pose.pose.position.y = Y
        cam_pose.pose.position.z = Z
        cam_pose.pose.orientation.x = GRIPPER_DOWN[0]
        cam_pose.pose.orientation.y = GRIPPER_DOWN[1]
        cam_pose.pose.orientation.z = GRIPPER_DOWN[2]
        cam_pose.pose.orientation.w = GRIPPER_DOWN[3]

        try:
            world_pose = self._tf_buffer.transform(
                cam_pose, 'world', timeout=Duration(seconds=1.0))
            # approach 15cm above the object so the arm doesn't collide with the table
            world_pose.pose.position.z += 0.15
            self._goal_pub.publish(world_pose)
            p = world_pose.pose.position
            self.get_logger().info(f'Goal published: x={p.x:.3f} y={p.y:.3f} z={p.z:.3f}')
        except Exception as e:
            self.get_logger().error(f'TF transform failed: {e}')


def main():
    rclpy.init()
    node = ObjectLocalizerNode()
    try:
        rclpy.spin(node)
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
