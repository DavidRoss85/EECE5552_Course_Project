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
from dataclasses import dataclass, field
from enum import Enum

from lerobot.cameras import CameraConfig
from lerobot.robots import RobotConfig


class ActionType(Enum):
    CARTESIAN_VELOCITY = "cartesian_velocity"
    JOINT_POSITION = "joint_position"
    JOINT_TRAJECTORY = "joint_trajectory"


class GripperActionType(Enum):
    TRAJECTORY = "trajectory"  # Use JointTrajectoryController for gripper
    ACTION = "action"  # Use GripperActionClient
    TOPIC = "topic"  # Publish a gripper position topic


@dataclass
class ROS2InterfaceConfig:
    # Namespace used by ros2_control / MoveIt2 nodes
    namespace: str = ""

    arm_joint_names: list[str] = field(
        default_factory=lambda: [
            "joint_1",
            "joint_2",
            "joint_3",
            "joint_4",
            "joint_5",
            "joint_6",
        ]
    )
    gripper_joint_name: str = "gripper_joint"
    gripper_topic_name: str = "/gripper_position"

    # Base link name for computing end effector pose / velocity
    # Only applicable for cartesian control
    base_link: str = "base_link"

    # Only applicable if velocity control is used.
    max_linear_velocity: float = 0.10
    max_angular_velocity: float = 0.25  # rad/s

    # Only applicable if position control is used.
    min_joint_positions: list[float] | None = None
    max_joint_positions: list[float] | None = None

    gripper_open_position: float = 0.0
    gripper_close_position: float = 1.0

    gripper_action_type: GripperActionType = GripperActionType.TRAJECTORY
    enable_gaze_input: bool = False
    gaze_topic_name: str = "/eye_gaze_xy"
    gaze_default_x: float = 0.0
    gaze_default_y: float = 0.0


def _ur12e_ros2_interface_defaults() -> ROS2InterfaceConfig:
    return ROS2InterfaceConfig(
        arm_joint_names=[
            "shoulder_pan_joint",
            "shoulder_lift_joint",
            "elbow_joint",
            "wrist_1_joint",
            "wrist_2_joint",
            "wrist_3_joint",
        ],
        gripper_action_type=GripperActionType.TOPIC,
        gripper_topic_name="/gripper_position",
        base_link="tool0",
        max_linear_velocity=1.0,
        max_angular_velocity=1.0,
    )


@dataclass
class ROS2Config(RobotConfig):
    # Action type for controlling the robot. Can be 'cartesian_velocity' or 'joint_position'.
    action_type: ActionType = ActionType.JOINT_POSITION

    # `max_relative_target` limits the magnitude of the relative positional target vector for safety purposes.
    # Set this to a positive scalar to have the same value for all motors, or a list that is the same length as
    # the number of motors in your follower arms.
    max_relative_target: int | None = None

    # cameras
    cameras: dict[str, CameraConfig] = field(default_factory=dict)

    # ROS2 interface configuration
    ros2_interface: ROS2InterfaceConfig = field(default_factory=ROS2InterfaceConfig)

    def apply_robot_specific_interface_defaults(self) -> None:
        pass


@RobotConfig.register_subclass("annin_ar4_mk1")
@dataclass
class AnninAR4Config(ROS2Config):
    """Annin Robotics AR4 robot configuration - extends ROS2Config with
    AR4-specific settings
    """

    action_type: ActionType = ActionType.CARTESIAN_VELOCITY

    ros2_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            gripper_joint_name="gripper_jaw1_joint",
            base_link="tool0",
            min_joint_positions=[-2.9671, -0.7330, -1.5533, -2.8798, -1.8326, -2.7053],
            max_joint_positions=[2.9671, 1.5708, 0.9076, 2.8798, 1.8326, 2.7053],
            gripper_open_position=0.014,
            gripper_close_position=0.0,
            gripper_action_type=GripperActionType.ACTION,
        ),
    )


@RobotConfig.register_subclass("ur12e_ros")
@dataclass
class UR12eROSConfig(ROS2Config):
    """UR12e in Gazebo with MoveIt Servo (Cartesian velocity).
    Compatible with EECE5552_Course_Project sim.launch.py.
    """

    action_type: ActionType = ActionType.CARTESIAN_VELOCITY

    ros2_interface: ROS2InterfaceConfig = field(
        default_factory=_ur12e_ros2_interface_defaults,
    )

    def __post_init__(self):
        parent_post_init = getattr(super(), "__post_init__", None)
        if callable(parent_post_init):
            parent_post_init()

        self.apply_robot_specific_interface_defaults()

    def apply_robot_specific_interface_defaults(self) -> None:

        # Some CLI/config parsers overwrite nested dataclass fields with base defaults
        # when only one subfield is overridden (e.g. enabling gaze input). Backfill
        # UR12e-specific defaults for fields that still match the generic ROS2 defaults.
        generic_defaults = ROS2InterfaceConfig()
        ur12e_defaults = _ur12e_ros2_interface_defaults()
        fields_to_backfill = (
            "arm_joint_names",
            "gripper_action_type",
            "gripper_topic_name",
            "base_link",
            "max_linear_velocity",
            "max_angular_velocity",
        )
        for field_name in fields_to_backfill:
            current = getattr(self.ros2_interface, field_name)
            generic = getattr(generic_defaults, field_name)
            if current == generic:
                ur12e = getattr(ur12e_defaults, field_name)
                setattr(self.ros2_interface, field_name, ur12e.copy() if isinstance(ur12e, list) else ur12e)


@RobotConfig.register_subclass("so101_ros")
@dataclass
class SO101ROSConfig(ROS2Config):
    """Configuration for the ROS 2 version of SO101: https://github.com/Pavankv92/lerobot_ws."""

    action_type: ActionType = ActionType.JOINT_TRAJECTORY

    ros2_interface: ROS2InterfaceConfig = field(
        default_factory=lambda: ROS2InterfaceConfig(
            arm_joint_names=["1", "2", "3", "4", "5"],
            gripper_joint_name="6",
            base_link="base",
            min_joint_positions=[-1.91986, -1.74533, -1.74533, -1.65806, -2.79253],
            max_joint_positions=[1.91986, 1.74533, 1.5708, 1.65806, 2.79253],
            gripper_open_position=1.74533,
            gripper_close_position=0.0,
        ),
    )
