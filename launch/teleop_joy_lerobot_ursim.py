"""Launch joy_node + teleop_twist_joy + home/gripper buttons.

Use this when running lerobot-teleoperate with --teleop.type=ros_twist.
The ros_twist teleop subscribes to /game_controller; this launch publishes there.
Press B to return arm to home pose.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        parameters=[
            {"deadzone": 0.15},
        ],
        output="screen",
    )

    teleop_node = Node(
        package="teleop_twist_joy",
        executable="teleop_node",
        name="teleop_twist_joy",
        remappings=[("/cmd_vel", "/game_controller")],
        parameters=[
            {"require_enable_button": True},
            {"enable_button": 7},
            {"axis_linear.x": 0},
            {"axis_linear.y": 1},
            {"axis_linear.z": 3},
            {"scale_linear.z": -0.5},
            {"scale_linear.x": -0.5},
            {"scale_linear.y": 0.5},
        ],
        output="screen",
    )

    home_button_node = Node(
        package="robot_control",
        executable="home_button_node",
        name="home_button_node",
        output="screen",
    )

    return LaunchDescription([joy_node, teleop_node, home_button_node])
