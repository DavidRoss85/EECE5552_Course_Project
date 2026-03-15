import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from cv_bridge import CvBridge
from ultralytics import YOLO

from robot_interfaces.msg import DetectedItem, DetectedList

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))


class DetectionNode(Node):
    def __init__(self):
        super().__init__('gaze_detection_node')

        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('rgb_topic', '/input/camera_feed/rgb/full_view')

        model_path = self.get_parameter('model').value
        self._conf_thresh = self.get_parameter('confidence_threshold').value
        rgb_topic = self.get_parameter('rgb_topic').value

        self._bridge = CvBridge()
        self._model = YOLO(model_path)
        self.get_logger().info(f'YOLO model loaded: {model_path}')

        self._pub = self.create_publisher(DetectedList, '/intent_selection/detections', 10)
        self.create_subscription(Image, rgb_topic, self._image_cb, 10)
        self.get_logger().info(f'Detection node ready, subscribing to {rgb_topic}')

    def _image_cb(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self._model(frame, conf=self._conf_thresh, verbose=False)

        out = DetectedList()
        out.header = Header()
        out.header.stamp = self.get_clock().now().to_msg()
        out.image_raw = msg

        for r in results:
            for i, box in enumerate(r.boxes):
                item = DetectedItem()
                item.name = self._model.names[int(box.cls[0])]
                item.index = i
                xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
                item.xyxy = xyxy
                x1, y1, x2, y2 = xyxy
                item.xywh = [x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2,
                              x2 - x1, y2 - y1]
                item.confidence = float(box.conf[0])
                out.item_list.append(item)

        # image_annotated intentionally empty — overlay node does its own drawing
        self._pub.publish(out)


def main():
    rclpy.init()
    node = DetectionNode()
    try:
        rclpy.spin(node)
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
