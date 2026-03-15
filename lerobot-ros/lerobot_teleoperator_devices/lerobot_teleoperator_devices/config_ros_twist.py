"""Config for ROS Twist teleoperator (subscribes to /game_controller from joy + teleop_twist_joy)."""

from dataclasses import dataclass

from lerobot.teleoperators.config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("ros_twist")
@dataclass
class RosTwistTeleopConfig(TeleoperatorConfig):
    use_gripper: bool = True
    twist_topic: str = "/game_controller"
