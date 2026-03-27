import threading
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
import rclpy
from rclpy.executors import Executor, SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image


@dataclass
class ROSTopicCameraConfig:
    topic: str
    width: int
    height: int


class ROSTopicCamera:
    """Camera interface that reads frames directly from a ROS2 Image topic."""

    def __init__(self, cfg: ROSTopicCameraConfig):
        self.cfg = cfg
        self.node: Node | None = None
        self.sub = None
        self.executor: Executor | None = None
        self.executor_thread: threading.Thread | None = None
        self._last_frame: np.ndarray | None = None
        self._last_frame_time = 0.0
        self._lock = threading.Lock()
        self.is_connected = False

    def connect(self) -> None:
        if self.is_connected:
            return
        if not rclpy.ok():
            rclpy.init()

        safe_name = self.cfg.topic.strip("/").replace("/", "_") or "image_raw"
        self.node = Node(f"ros_topic_camera_{safe_name}")
        self.sub = self.node.create_subscription(Image, self.cfg.topic, self._cb, 10)
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor_thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()
        self.is_connected = True

    def disconnect(self) -> None:
        if self.sub:
            self.sub.destroy()
            self.sub = None
        if self.node:
            self.node.destroy_node()
            self.node = None
        if self.executor:
            self.executor.shutdown()
            self.executor = None
        if self.executor_thread:
            self.executor_thread.join(timeout=1.0)
            self.executor_thread = None
        self.is_connected = False

    def async_read(self, timeout_ms: int = 300) -> np.ndarray:
        deadline = time.perf_counter() + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            with self._lock:
                if self._last_frame is not None:
                    return self._last_frame.copy()
            time.sleep(0.001)
        raise TimeoutError(
            f"Timed out waiting for frame from ROS topic {self.cfg.topic} after {timeout_ms} ms."
        )

    def _cb(self, msg: Image) -> None:
        frame = self._image_to_bgr(msg)
        if frame is None:
            return
        if frame.shape[1] != self.cfg.width or frame.shape[0] != self.cfg.height:
            frame = cv2.resize(frame, (self.cfg.width, self.cfg.height), interpolation=cv2.INTER_LINEAR)
        with self._lock:
            self._last_frame = frame
            self._last_frame_time = time.perf_counter()

    @staticmethod
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


def is_ros_topic_camera(camera_cfg: Any) -> bool:
    index_or_path = getattr(camera_cfg, "index_or_path", None)
    if index_or_path is None:
        return False
    s = str(index_or_path)
    return s.startswith("ros:/")


def parse_ros_topic(index_or_path: str | Any) -> str:
    s = str(index_or_path)
    # Accept ros:///foo/bar, ros://foo/bar, ros:/foo/bar (parser may normalize to Path)
    for prefix in ("ros://", "ros:/"):
        if s.startswith(prefix):
            topic = s[len(prefix) :]
            break
    else:
        topic = s
    if not topic.startswith("/"):
        topic = "/" + topic
    return topic
