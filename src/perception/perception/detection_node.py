import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge
from robot_interfaces.msg import DetectedList, DetectedItem

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

# HSV ranges: each color is a list of (lower, upper) tuples
# Red wraps around 180 so it needs two ranges
HSV_RANGES = {
    # Broad red bands to tolerate webcam color shift toward orange/magenta.
    'red':    [((0,    50,  40), (25,  255, 255)),
               ((155,  50,  40), (180, 255, 255))],
    'blue':   [((100, 100, 100), (130, 255, 255))],
    'yellow': [((20,  100, 100), (35,  255, 255))],
}

MIN_CONTOUR_AREA = 150  # px^2 — filters out noise blobs
_MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))


class DetectionNode(Node):
    def __init__(self):
        super().__init__('detection_node')

        self.declare_parameter('camera_source', 'topic')   # 'topic' or 'usb'
        self.declare_parameter('camera_topic', '/input/camera_feed/rgb/full_view')
        self.declare_parameter('camera_device', '/dev/video0')
        self.declare_parameter('image_width', 1280)
        self.declare_parameter('image_height', 720)

        self._source = self.get_parameter('camera_source').value
        self._bridge = CvBridge()
        self._cap = None

        self._det_pub = self.create_publisher(DetectedList, '/perception/detections', 10)
        self._img_pub = self.create_publisher(Image, '/perception/camera_image', 10)

        if self._source == 'usb':
            device = self.get_parameter('camera_device').value
            try:
                cam_arg = int(device)
            except (ValueError, TypeError):
                cam_arg = device  # pass string path directly to VideoCapture
            self._cap = cv2.VideoCapture(cam_arg)
            w = self.get_parameter('image_width').value
            h = self.get_parameter('image_height').value
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            self.create_timer(1.0 / 30.0, self._usb_cb)
            self.get_logger().info(f'Detection node: USB camera {cam_arg}')
        else:
            topic = self.get_parameter('camera_topic').value
            self.create_subscription(Image, topic, self._topic_cb, 10)
            self.get_logger().info(f'Detection node: ROS topic {topic}')

    def _topic_cb(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self._process(frame, msg.header)

    def _usb_cb(self):
        if self._cap is None or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = 'camera'
        self._process(frame, header)

    def _process(self, frame, header):
        # Always republish raw image so gaze_overlay_node can subscribe
        img_msg = self._bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header = header
        self._img_pub.publish(img_msg)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        det_list = DetectedList()
        det_list.header = header

        for color_name, ranges in HSV_RANGES.items():
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for (lo, hi) in ranges:
                mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))

            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _MORPH_KERNEL)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _MORPH_KERNEL)

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) < MIN_CONTOUR_AREA:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                cx, cy = x + w // 2, y + h // 2

                item = DetectedItem()
                item.name = color_name
                item.xyxy = [x, y, x + w, y + h]
                item.xywh = [cx, cy, w, h]
                item.confidence = 1.0
                det_list.item_list.append(item)

        self._det_pub.publish(det_list)


def main():
    rclpy.init()
    node = DetectionNode()
    try:
        rclpy.spin(node)
    finally:
        if node._cap is not None:
            node._cap.release()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
