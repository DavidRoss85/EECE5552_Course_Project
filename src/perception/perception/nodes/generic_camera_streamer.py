"""
Camera Publisher Node

Captures frames from a camera device and publishes them to a ROS2 image topic.

This node is intentionally simple and configurable so it can support
multiple camera setups via parameters passed from launch files.
"""

# ROS2 imports
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

# OpenCV
import cv2
from cv_bridge import CvBridge

from perception.config.ros_presets import STD_CFG

class CameraPublisherNode(Node):

    def __init__(self):
        super().__init__("camera_publisher_node")

        self.get_logger().info("Initializing Camera Publisher Node...")

        # Configurations
        self._ros_config = STD_CFG

        # --------------------------------------------------
        # Declare parameters (can be overridden in launch)
        # --------------------------------------------------

        self.declare_parameter("camera_device", 0)
        self.declare_parameter("publish_topic", self._ros_config.topic_full_view_rgb)
        self.declare_parameter("frame_rate", 30)

        self._camera_device = self.get_parameter("camera_device").value
        self._publish_topic = self.get_parameter("publish_topic").value
        self._frame_rate = self.get_parameter("frame_rate").value

        # --------------------------------------------------
        # OpenCV camera initialization
        # --------------------------------------------------

        self._camera = cv2.VideoCapture(self._camera_device)

        if not self._camera.isOpened():
            self.get_logger().error(
                f"Failed to open camera device: {self._camera_device}"
            )
            raise RuntimeError("Camera device could not be opened")

        self.get_logger().info(f"Camera device {self._camera_device} opened")

        # --------------------------------------------------
        # ROS publisher
        # --------------------------------------------------

        self._image_publisher = self.create_publisher(
            Image,
            self._publish_topic,
            self._ros_config.max_messages
        )

        self.get_logger().info(
            f"Publishing camera frames on topic: {self._publish_topic}"
        )


        # Image conversion bridge
        self._bridge = CvBridge()


        # Timer to capture frames
        timer_period = 1.0 / self._frame_rate

        self._timer = self.create_timer(
            timer_period,
            self._publish_frame
        )

    # --------------------------------------------------

    def _publish_frame(self):
        """
        Capture frame from camera and publish it.
        """

        ret, frame = self._camera.read()

        if not ret:
            self.get_logger().warn("Failed to capture frame")
            return

        # Convert OpenCV frame to ROS Image message
        msg = self._bridge.cv2_to_imgmsg(frame, encoding="bgr8")

        # Publish frame
        self._image_publisher.publish(msg)

    # --------------------------------------------------

    def destroy_node(self):
        """
        Ensure camera device is released when node shuts down.
        """
        if hasattr(self, "_camera"):
            self._camera.release()

        super().destroy_node()


# --------------------------------------------------


def main(args=None):

    rclpy.init(args=args)

    node = CameraPublisherNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()