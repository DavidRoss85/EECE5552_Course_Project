# Author: abdul rahman
# mohammedabdulr.1@northeastern.edu

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    # Bridge gz camera topics → ROS2 topics
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_camera_bridge',
        arguments=[
            '/cameras/top/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/cameras/side/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/cameras/front/image_raw@sensor_msgs/msg/Image[gz.msgs.Image',
            '/cameras/top/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/cameras/side/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/cameras/front/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        output='screen'
    )

    return LaunchDescription([gz_bridge])
