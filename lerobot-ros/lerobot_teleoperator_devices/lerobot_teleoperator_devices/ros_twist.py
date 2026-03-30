"""
Teleoperator that forwards geometry_msgs/Twist from a ROS topic as 6-DOF actions.

Use with joy_node + teleop_twist_joy publishing to /game_controller.
Run joy + teleop_twist_joy in a separate terminal.
"""

import threading
import time
from typing import Any

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Joy

from lerobot.teleoperators import Teleoperator

from .config_ros_twist import RosTwistTeleopConfig


class RosTwistTeleop(Teleoperator):
    """
    Teleoperator that forwards geometry_msgs/Twist from a ROS topic (e.g. /game_controller
    from joy_node + teleop_twist_joy) as 6-DOF actions. Use with lerobot-teleoperate.
    """

    config_class = RosTwistTeleopConfig
    name = "ros_twist"

    def __init__(self, config: RosTwistTeleopConfig):
        super().__init__(config)
        self.config = config
        self.robot_type = config.type
        self.running = True
        self.episode_end_status = None
        self._node: Node | None = None
        self._executor: SingleThreadedExecutor | None = None
        self._thread: threading.Thread | None = None
        self._last_twist: Twist | None = None
        self._gripper_pos: float = 1.0  # 0.0=closed, 1.0=open; start open
        self._a_prev: bool = False       # previous A button state for edge detection
        self._lock = threading.Lock()

    @property
    def action_features(self) -> dict:
        if self.config.use_gripper:
            return {
                "dtype": "float32",
                "shape": (7,),
                "names": {
                    "linear_x.vel": 0,
                    "linear_y.vel": 1,
                    "linear_z.vel": 2,
                    "angular_x.vel": 3,
                    "angular_y.vel": 4,
                    "angular_z.vel": 5,
                    "gripper.pos": 6,
                },
            }
        return {
            "dtype": "float32",
            "shape": (6,),
            "names": {
                "linear_x.vel": 0,
                "linear_y.vel": 1,
                "linear_z.vel": 2,
                "angular_x.vel": 3,
                "angular_y.vel": 4,
                "angular_z.vel": 5,
            },
        }

    @property
    def feedback_features(self) -> dict:
        return {}

    def connect(self) -> None:
        if not rclpy.ok():
            rclpy.init()
        self._node = Node("ros_twist_teleop_node")
        self._node.create_subscription(
            Twist,
            self.config.twist_topic,
            self._twist_cb,
            10,
        )
        if self.config.use_gripper:
            self._node.create_subscription(
                Joy,
                self.config.joy_topic,
                self._joy_cb,
                10,
            )
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()
        time.sleep(0.5)

    def _twist_cb(self, msg: Twist) -> None:
        with self._lock:
            self._last_twist = msg

    def _joy_cb(self, msg: Joy) -> None:
        btn = self.config.gripper_button
        if btn >= len(msg.buttons):
            return
        a_pressed = bool(msg.buttons[btn])
        # Toggle on rising edge (press, not hold)
        with self._lock:
            if a_pressed and not self._a_prev:
                print(f"Gripper button pressed: {a_pressed}")
                self._gripper_pos = 0.0 if self._gripper_pos >= 0.5 else 1.0
            self._a_prev = a_pressed

    def get_action(self) -> dict[str, Any]:
        if self._node is None:
            raise RuntimeError("ROS Twist teleop not connected. Call connect() first.")
        with self._lock:
            t = self._last_twist
            gripper = self._gripper_pos
        if t is None:
            return self._zero_action()
        action_dict: dict[str, Any] = {
            "linear_x.vel": float(t.linear.y),
            "linear_y.vel": float(t.linear.x),
            "linear_z.vel": float(t.linear.z),
            "angular_x.vel": float(t.angular.x),
            "angular_y.vel": float(t.angular.y),
            "angular_z.vel": float(t.angular.z),
        }
        if self.config.use_gripper:
            action_dict["gripper.pos"] = gripper
        return action_dict

    def _zero_action(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "linear_x.vel": 0.0,
            "linear_y.vel": 0.0,
            "linear_z.vel": 0.0,
            "angular_x.vel": 0.0,
            "angular_y.vel": 0.0,
            "angular_z.vel": 0.0,
        }
        if self.config.use_gripper:
            with self._lock:
                out["gripper.pos"] = self._gripper_pos
        return out

    def disconnect(self) -> None:
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        with self._lock:
            self._last_twist = None

    def is_connected(self) -> bool:
        return self._node is not None

    def calibrate(self) -> None:
        pass

    def is_calibrated(self) -> bool:
        return True

    def configure(self) -> None:
        pass

    def send_feedback(self, feedback: dict) -> None:
        pass
