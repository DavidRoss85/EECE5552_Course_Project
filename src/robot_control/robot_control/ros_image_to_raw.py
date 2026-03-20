"""Stream a ROS Image topic as raw BGR video to stdout for piping to ffmpeg.

Usage:
  ros2 run robot_control ros_image_to_raw --topic /cameras/top/image_raw | \
    ffmpeg -y -loglevel error -f rawvideo -pix_fmt bgr24 -s 640x480 -r 30 \\
      -i pipe:0 -f v4l2 -pix_fmt rgb24 /dev/video10

Or with args:
  ros_image_to_raw --topic /cameras/top/image_raw --width 640 --height 480 | ffmpeg ...
"""

import argparse
import queue
import sys
import threading

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


def _image_to_bgr(msg: Image) -> np.ndarray | None:
    if msg.encoding not in ("rgb8", "bgr8", "rgba8", "bgra8", "mono8"):
        return None
    channels = 3 if msg.encoding in ("rgb8", "bgr8") else (4 if msg.encoding in ("rgba8", "bgra8") else 1)
    expected = msg.height * msg.step
    data = np.frombuffer(msg.data, dtype=np.uint8)
    if data.size < expected:
        return None
    frame = data[:expected].reshape((msg.height, msg.step))
    frame = frame[:, : msg.width * channels].reshape((msg.height, msg.width, channels))
    if msg.encoding == "rgb8":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    elif msg.encoding == "rgba8":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    elif msg.encoding == "bgra8":
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    elif msg.encoding == "mono8":
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    return frame


class RosImageToRaw(Node):
    def __init__(self, topic: str, width: int, height: int):
        super().__init__("ros_image_to_raw")
        self.topic = topic
        self.width = width
        self.height = height
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=2)
        self._stop = threading.Event()
        self._writer = threading.Thread(target=self._write_loop, daemon=True)
        self._writer.start()
        self.create_subscription(Image, topic, self._cb, 10)
        self.get_logger().info(
            f"Streaming {topic} -> stdout (BGR {width}x{height})"
        )

    def _cb(self, msg: Image) -> None:
        frame = _image_to_bgr(msg)
        if frame is None:
            return
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(
                frame, (self.width, self.height),
                interpolation=cv2.INTER_LINEAR,
            )
        try:
            self._queue.put_nowait(frame.astype(np.uint8))
        except queue.Full:
            pass

    def _write_loop(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                sys.stdout.buffer.write(frame.tobytes())
                sys.stdout.buffer.flush()
            except BrokenPipeError:
                return
            except OSError:
                return

    def destroy_node(self) -> bool:
        self._stop.set()
        self._writer.join(timeout=2.0)
        return super().destroy_node()


def main():
    parser = argparse.ArgumentParser(
        description="Stream ROS Image topic as raw BGR to stdout for ffmpeg"
    )
    parser.add_argument("--topic", "-t", default="/cameras/top/image_raw")
    parser.add_argument("--width", "-w", type=int, default=640)
    parser.add_argument("--height", "-H", type=int, default=480)
    args = parser.parse_args()

    rclpy.init()
    node = RosImageToRaw(args.topic, args.width, args.height)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
