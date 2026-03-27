"""Launch URSim stack and joystick teleop together.

Usage:
  ros2 launch EECE5552_Course_Project ursim_with_joy_teleop.launch.py
  ros2 launch EECE5552_Course_Project ursim_with_joy_teleop.launch.py robot_ip:=<ip>
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    launch_dir = os.path.dirname(os.path.abspath(__file__))
    robot_ip = LaunchConfiguration("robot_ip")

    robot_ip_arg = DeclareLaunchArgument(
        "robot_ip",
        default_value="10.245.216.50",
        description="IP address of the URSim instance",
    )

    ursim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, "ursim.launch.py")),
        launch_arguments={"robot_ip": robot_ip}.items(),
    )

    teleop_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, "teleop_joy_lerobot_ursim.py"))
    )

    return LaunchDescription(
        [
            robot_ip_arg,
            ursim_launch,
            teleop_launch,
        ]
    )
