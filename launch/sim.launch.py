# Author: abdul rahman
# mohammedabdulr.1@northeastern.edu

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
from ament_index_python.packages import get_package_share_directory
from launch_param_builder import ParameterBuilder


def generate_launch_description():

    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    world_file = os.path.join(pkg_dir, 'simulation', 'worlds', 'ur12e_table.world')
    desc_file  = os.path.join(pkg_dir, 'simulation', 'assets', 'ur12e_table_mounted.urdf.xacro')

    gazebo_and_controllers = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ur_simulation_gz'),
                'launch',
                'ur_sim_control.launch.py'
            )
        ),
        launch_arguments={
            'ur_type':          'ur12e',
            'world_file':       world_file,
            'description_file': desc_file,
            'launch_rviz':      'false',
            'gazebo_gui':       'true',
        }.items()
    )

    moveit_config = (
        MoveItConfigsBuilder('ur', package_name='ur_moveit_config')
        .robot_description_semantic('srdf/ur.srdf.xacro', {'name': 'ur12e'})
        .to_moveit_configs()
    )

    servo_params = {
        "moveit_servo": ParameterBuilder("ur_moveit_config")
        .yaml("config/ur_servo.yaml")
        .to_dict()
    }

    acceleration_filter_update_period = {"update_period": 0.01}

    servo_node = Node(
        package="moveit_servo",
        executable="servo_node",
        parameters=[
            servo_params,
            acceleration_filter_update_period,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics, # here is where kinematics plugin parameters are passed
            {"use_sim_time": True},
        ],
    )

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            moveit_config.to_dict(),
            {'use_sim_time': True},
            {'publish_robot_description_semantic': True},
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='log',
        arguments=['-d', os.path.join(
            get_package_share_directory('ur_moveit_config'),
            'config', 'moveit.rviz'
        )],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            {'use_sim_time': True},
        ],
    )

    # bridge gz camera topics to ROS2
    camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='camera_bridge',
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

    moveit = TimerAction(
        period=10.0,
        actions=[move_group_node, rviz_node]
    )

    cameras = TimerAction(
        period=15.0,
        actions=[camera_bridge]
    )

    return LaunchDescription([
        gazebo_and_controllers,
        moveit,
        cameras,
        servo_node,
    ])
