#!/usr/bin/env python3
"""SDK-based UR12e evaluation template with gaze x/y input.

This script demonstrates the standard realtime inference loop:
1) get observation
2) run policy
3) send action

It publishes gaze as std_msgs/Float32MultiArray on /eye_gaze_xy and relies on the
lerobot-ros integration to include gaze_x/gaze_y in observations.

`load_policy()` is intentionally left unimplemented.
"""

from __future__ import annotations

import argparse
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray

from lerobot_robot_ros.config import UR12eROSConfig
from lerobot_robot_ros.robot import UR12eROS


class GazePublisher(Node):
    def __init__(self, topic_name: str, rate_hz: float):
        super().__init__("gaze_eval_publisher")
        self._pub = self.create_publisher(Float32MultiArray, topic_name, 10)
        self.x = 0.5
        self.y = 0.5
        self._timer = self.create_timer(1.0 / rate_hz, self._tick)

    def _tick(self) -> None:
        msg = Float32MultiArray()
        msg.data = [float(self.x), float(self.y)]
        self._pub.publish(msg)


def load_policy(_checkpoint_path: str):
    """Load and return a policy object with a select_action(obs) method."""
    raise NotImplementedError("Implement policy loading for your LeRobot version")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate UR12e policy with SDK + gaze topic")
    parser.add_argument("--checkpoint-path", required=True, help="Path to policy checkpoint/pretrained_model")
    parser.add_argument("--duration-s", type=float, default=20.0, help="Evaluation rollout duration in seconds")
    parser.add_argument("--control-rate-hz", type=float, default=30.0, help="Control loop frequency")
    parser.add_argument("--gaze-topic", default="/eye_gaze_xy", help="ROS topic for gaze [x,y]")
    parser.add_argument("--gaze-rate-hz", type=float, default=30.0, help="Gaze publish frequency")
    parser.add_argument("--gaze-x", type=float, default=0.5, help="Initial gaze x")
    parser.add_argument("--gaze-y", type=float, default=0.5, help="Initial gaze y")
    parser.add_argument(
        "--gaze-stale-timeout-s",
        type=float,
        default=0.5,
        help="Seconds before gaze falls back to default (0.0 means never stale after first sample)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rclpy.init()

    gaze_node = GazePublisher(topic_name=args.gaze_topic, rate_hz=args.gaze_rate_hz)
    gaze_node.x = args.gaze_x
    gaze_node.y = args.gaze_y

    executor = SingleThreadedExecutor()
    executor.add_node(gaze_node)

    robot = None
    try:
        cfg = UR12eROSConfig()
        cfg.ros2_interface.enable_gaze_input = True
        cfg.ros2_interface.gaze_topic_name = args.gaze_topic
        cfg.ros2_interface.gaze_stale_timeout_s = args.gaze_stale_timeout_s
        cfg.ros2_interface.gaze_default_x = args.gaze_x
        cfg.ros2_interface.gaze_default_y = args.gaze_y

        robot = UR12eROS(cfg)
        robot.connect()

        policy = load_policy(args.checkpoint_path)

        period_s = 1.0 / args.control_rate_hz
        end_t = time.monotonic() + args.duration_s

        while time.monotonic() < end_t:
            t0 = time.monotonic()
            executor.spin_once(timeout_sec=0.0)

            obs = robot.get_observation()
            action = policy.select_action(obs)
            robot.send_action(action)

            dt = time.monotonic() - t0
            sleep_s = period_s - dt
            if sleep_s > 0.0:
                time.sleep(sleep_s)

    except KeyboardInterrupt:
        pass
    finally:
        if robot is not None:
            try:
                robot.disconnect()
            except Exception:
                pass
        gaze_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
