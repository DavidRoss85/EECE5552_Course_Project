"""
Generic Image Viewer Node

Subscribes to a ROS2 image topic and displays the image using OpenCV.
Useful for debugging camera feeds and perception pipelines.
"""

# ROS2 imports
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

# OpenCV
import cv2
from cv_bridge import CvBridge

from perception.config.ros_presets import STD_CFG

class ImageViewerNode(Node):

    def __init__(self):
        super().__init__("image_viewer_node")

        self.get_logger().info("Initializing Image Viewer Node...")

        # --------------------------------------------------
        # Parameters
        # --------------------------------------------------

        self.declare_parameter("image_topic", "/camera/rgb")

        self._image_topic = self.get_parameter("image_topic").value
        self._image_topic = STD_CFG.topic_full_view_rgb   # Override with config value
        # --------------------------------------------------
        # CV bridge
        # --------------------------------------------------

        self._bridge = CvBridge()

        # --------------------------------------------------
        # Subscriber
        # --------------------------------------------------

        self._image_subscriber = self.create_subscription(
            Image,
            self._image_topic,
            self._image_callback,
            10
        )

        self.get_logger().info(
            f"Subscribed to image topic: {self._image_topic}"
        )

    # --------------------------------------------------

    def _image_callback(self, message: Image):
        """
        Receives image messages and displays them.
        """

        try:

            frame = self._bridge.imgmsg_to_cv2(message, "bgr8")

            cv2.imshow("Image Viewer", frame)
            cv2.waitKey(1)

        except Exception as e:

            self.get_logger().error(
                f"Failed to process image frame: {str(e)}"
            )


# --------------------------------------------------


def main(args=None):

    rclpy.init()

    node = ImageViewerNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()