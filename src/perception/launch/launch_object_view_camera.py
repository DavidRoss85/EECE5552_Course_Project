from launch import LaunchDescription
from launch_ros.actions import Node

from perception.config.ros_presets import STD_CFG

def generate_launch_description():
    return LaunchDescription([
        Node(
            package="perception",
            executable="camera_streamer",
            parameters=[{
                "camera_device": 0,
                "publish_topic": STD_CFG.topic_object_view_rgb,
                "frame_rate": 30
            }]
        )
    ])

