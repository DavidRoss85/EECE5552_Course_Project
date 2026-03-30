# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import threading
import time

import rclpy
from control_msgs.action import GripperCommand
from lerobot.utils.errors import DeviceNotConnectedError
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import Executor, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.publisher import Publisher
from sensor_msgs.msg import JointState
from std_msgs.msg import Float32MultiArray, Float64, Float64MultiArray
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from .config import ActionType, GripperActionType, ROS2InterfaceConfig
from .moveit_servo import MoveIt2Servo

logger = logging.getLogger(__name__)


class ROS2Interface:
    """Class to interface with a MoveIt2 manipulator.

    This class supports both JointGroupPositionController and JointTrajectoryController
    from ros2_control for arm control, depending on the configuration:

    - ActionType.JOINT_POSITION:
      Uses JointGroupPositionController.
      Publishes Float64MultiArray messages to '/position_controller/commands'

    - ActionType.JOINT_TRAJECTORY:
      Uses JointTrajectoryController.
      Publishes JointTrajectory messages to '/arm_controller/joint_trajectory'

    The gripper control also supports both trajectory and action-based control
    via the gripper_action_type configuration option.
    """

    def __init__(self, config: ROS2InterfaceConfig, action_type: ActionType):
        self.config = config
        self.action_type = action_type
        self.robot_node: Node | None = None
        self.pos_cmd_pub: Publisher | None = None
        self.traj_cmd_pub: Publisher | None = None
        self.gripper_action_client: ActionClient | None = None
        self.gripper_traj_pub: Publisher | None = None
        self.gripper_topic_pub: Publisher | None = None
        self.executor: Executor | None = None
        self.moveit2_servo: MoveIt2Servo | None = None
        self.executor_thread: threading.Thread | None = None
        self.is_connected = False
        self._last_joint_state: dict[str, dict[str, float]] | None = None
        self._last_gripper_position: float | None = None
        self._last_published_gripper: float | None = None  # dedup for TOPIC mode
        self._last_gaze_xy: tuple[float, float] | None = None
        self.gaze_sub = None
        self.joint_state_sub = None

    def connect(self) -> None:
        if not rclpy.ok():
            rclpy.init()

        self.robot_node = Node("moveit2_interface_node", namespace=self.config.namespace)
        if self.action_type == ActionType.JOINT_POSITION:
            self.pos_cmd_pub = self.robot_node.create_publisher(
                Float64MultiArray, "/position_controller/commands", 10
            )
        elif self.action_type == ActionType.JOINT_TRAJECTORY:
            self.traj_cmd_pub = self.robot_node.create_publisher(
                JointTrajectory, "/arm_controller/joint_trajectory", 10
            )
        elif self.action_type == ActionType.CARTESIAN_VELOCITY:
            self.moveit2_servo = MoveIt2Servo(
                node=self.robot_node,
                frame_id=self.config.base_link,
                callback_group=ReentrantCallbackGroup(),
            )

        if self.config.gripper_action_type == GripperActionType.TRAJECTORY:
            self.gripper_traj_pub = self.robot_node.create_publisher(
                JointTrajectory, "/gripper_controller/joint_trajectory", 10
            )
        elif self.config.gripper_action_type == GripperActionType.TOPIC:
            self.gripper_topic_pub = self.robot_node.create_publisher(
                Float64, self.config.gripper_topic_name, 10
            )
        else:
            self.gripper_action_client = ActionClient(
                self.robot_node,
                GripperCommand,
                "/gripper_controller/gripper_cmd",
                callback_group=ReentrantCallbackGroup(),
            )
            self._goal_msg = GripperCommand.Goal()

        self.joint_state_sub = self.robot_node.create_subscription(
            JointState,
            "joint_states",
            self._joint_state_callback,
            10,
        )
        if self.config.enable_gaze_input:
            self.gaze_sub = self.robot_node.create_subscription(
                Float32MultiArray,
                self.config.gaze_topic_name,
                self._gaze_callback,
                10,
            )

        # Create and start the executor in a separate thread
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.robot_node)
        self.executor_thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()
        time.sleep(3)  # Give some time to connect to services and receive messages

        self.is_connected = True

    def send_joint_position_command(self, joint_positions: list[float], unnormalize: bool = True) -> None:
        """
        Send a command to the robot's joints.
        Args:
            joint_positions (list[float]): The target positions for the joints.
            unnormalize (bool): Whether to unnormalize the joint positions based on the robot's configuration.
        """
        if not self.robot_node:
            raise DeviceNotConnectedError("ROS2Interface is not connected. You need to call `connect()`.")

        if unnormalize:
            if self.config.min_joint_positions is None or self.config.max_joint_positions is None:
                raise ValueError(
                    "Joint position normalization requires min and max joint positions to be set."
                )
            joint_positions = [
                min(max(pos, min_pos), max_pos)
                for pos, min_pos, max_pos in zip(
                    joint_positions,
                    self.config.min_joint_positions,
                    self.config.max_joint_positions,
                    strict=True,
                )
            ]

        if len(joint_positions) != len(self.config.arm_joint_names):
            raise ValueError(
                f"Expected {len(self.config.arm_joint_names)} joint positions, but got {len(joint_positions)}."
            )

        if self.action_type == ActionType.JOINT_TRAJECTORY:
            if self.traj_cmd_pub is None:
                raise DeviceNotConnectedError("Trajectory command publisher is not initialized.")
            msg = JointTrajectory()
            msg.joint_names = self.config.arm_joint_names
            point = JointTrajectoryPoint()
            point.positions = joint_positions
            msg.points = [point]
            self.traj_cmd_pub.publish(msg)
        else:
            if self.pos_cmd_pub is None:
                raise DeviceNotConnectedError("Position command publisher is not initialized.")
            msg = Float64MultiArray()
            msg.data = joint_positions
            self.pos_cmd_pub.publish(msg)

    def servo(self, linear, angular, normalize: bool = True) -> None:
        if not self.moveit2_servo:
            raise DeviceNotConnectedError("ROS2Interface is not connected. You need to call `connect()`.")

        if normalize:
            linear = [v * self.config.max_linear_velocity for v in linear]
            angular = [v * self.config.max_angular_velocity for v in angular]
        self.moveit2_servo.servo(linear=linear, angular=angular)

    def send_gripper_command(self, position: float, unnormalize: bool = True) -> bool:
        """
        Send a command to the gripper to move to a specific position.
        Args:
            position (float): The target position for the gripper (0=closed, 1=open).
        Returns:
            bool: True if the command was sent successfully, False otherwise.
        """
        if not self.robot_node:
            raise DeviceNotConnectedError("ROS2Interface is not connected. You need to call `connect()`.")

        if unnormalize:
            # Map normalized position (0=closed, 1=open) to actual gripper joint position
            open_pos = self.config.gripper_open_position
            closed_pos = self.config.gripper_close_position
            gripper_goal = open_pos + position * (closed_pos - open_pos)
        else:
            gripper_goal = position

        if self.config.gripper_action_type == GripperActionType.TRAJECTORY:
            if self.gripper_traj_pub is None:
                raise DeviceNotConnectedError("Gripper command publisher is not initialized.")
            msg = JointTrajectory()
            msg.joint_names = [self.config.gripper_joint_name]
            point = JointTrajectoryPoint()
            point.positions = [float(gripper_goal)]
            msg.points = [point]
            self.gripper_traj_pub.publish(msg)
            return True
        elif self.config.gripper_action_type == GripperActionType.TOPIC:
            if self.gripper_topic_pub is None:
                raise DeviceNotConnectedError("Gripper topic publisher is not initialized.")
            value = float(position)
            if value == self._last_published_gripper:
                return True  # no state change, don't publish
            msg = Float64()
            msg.data = value
            self.gripper_topic_pub.publish(msg)
            self._last_published_gripper = value
            self._last_gripper_position = value
            return True
        else:
            if not self.gripper_action_client:
                raise DeviceNotConnectedError("Gripper action client is not initialized.")

            if not self.gripper_action_client.wait_for_server(timeout_sec=1.0):
                logger.error("Gripper action server not available")
                return False

            self._goal_msg.command.position = float(gripper_goal)
            if not (resp := self.gripper_action_client.send_goal(self._goal_msg)):
                logger.error("Failed to send gripper command")
                return False
            result = resp.result  # type: ignore  # ROS2 types available at runtime
            if result.reached_goal:
                self._last_gripper_position = float(position)
                return True
            logger.error(
                f"Gripper did not reach goal. stalled: {result.stalled}, "
                f"effort: {result.effort}, position: {result.position}"
            )
            return False

    @property
    def joint_state(self) -> dict[str, dict[str, float]] | None:
        """Get the last received joint state."""
        return self._last_joint_state

    def _joint_state_callback(self, msg: "JointState") -> None:
        positions: dict[str, float] = {}
        velocities: dict[str, float] = {}
        name_to_index = {name: i for i, name in enumerate(msg.name)}
        for joint_name in self.config.arm_joint_names:
            idx = name_to_index.get(joint_name)
            if idx is None:
                logger.warning(
                    f"Joint '{joint_name}' not found in joint state. "
                    f"Received joints: {list(msg.name)}"
                )
                return
            positions[joint_name] = msg.position[idx]
            velocities[joint_name] = msg.velocity[idx]

        if self.config.gripper_joint_name:
            idx = name_to_index.get(self.config.gripper_joint_name)
            if idx is not None:
                positions[self.config.gripper_joint_name] = msg.position[idx]
                velocities[self.config.gripper_joint_name] = msg.velocity[idx]
            else:
                gripper_key = self.config.gripper_joint_name
                positions[gripper_key] = self._last_gripper_position if self._last_gripper_position is not None else 0.0
                velocities[gripper_key] = 0.0

        self._last_joint_state = {"position": positions, "velocity": velocities}

    @property
    def gaze_xy(self) -> tuple[float, float] | None:
        """Get the last received gaze [x, y] sample."""
        return self._last_gaze_xy

    def _gaze_callback(self, msg: "Float32MultiArray") -> None:
        if len(msg.data) < 2:
            logger.warning(
                f"Received gaze message with {len(msg.data)} value(s) on "
                f"{self.config.gaze_topic_name}; expected at least 2."
            )
            return
        logger.info(f"Received gaze message: {msg.data[0]}, {msg.data[1]}")
        print(f"Received gaze message: {msg.data[0]}, {msg.data[1]}")
        self._last_gaze_xy = (float(msg.data[0]), float(msg.data[1]))

    def disconnect(self):
        if self.joint_state_sub:
            self.joint_state_sub.destroy()
            self.joint_state_sub = None
        if self.gaze_sub:
            self.gaze_sub.destroy()
            self.gaze_sub = None
        if self.pos_cmd_pub:
            self.pos_cmd_pub.destroy()
            self.pos_cmd_pub = None
        if self.traj_cmd_pub:
            self.traj_cmd_pub.destroy()
            self.traj_cmd_pub = None
        if self.gripper_action_client:
            self.gripper_action_client.destroy()
            self.gripper_action_client = None
        if self.gripper_traj_pub:
            self.gripper_traj_pub.destroy()
            self.gripper_traj_pub = None
        if self.gripper_topic_pub:
            self.gripper_topic_pub.destroy()
            self.gripper_topic_pub = None
        if self.robot_node:
            self.robot_node.destroy_node()
            self.robot_node = None
        if self.moveit2_servo:
            self.moveit2_servo = None

        if self.executor:
            self.executor.shutdown()
            self.executor = None
        if self.executor_thread:
            self.executor_thread.join()
            self.executor_thread = None

        self.is_connected = False
