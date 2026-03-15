# Author: abdul rahman
# mohammedabdulr.1@northeastern.edu

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
from ament_index_python.packages import get_package_share_directory


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
            '/cameras/top/depth@sensor_msgs/msg/Image[gz.msgs.Image',
        ],
        output='screen'
    )

    topic_relay = Node(
        package='topic_tools',
        executable='relay',
        name='top_camera_relay',
        arguments=['/cameras/top/image_raw', '/input/camera_feed/rgb/full_view'],
        output='screen'
    )

    camera_top_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_top_tf',
        arguments=['--x', '0.3', '--y', '0', '--z', '2.2',
                   '--roll', '3.14159', '--pitch', '0', '--yaw', '0',
                   '--frame-id', 'world',
                   '--child-frame-id', 'camera_top_optical_frame'],
        output='screen'
    )

    goal_controller_node = Node(
        package='robot_control',
        executable='goal_controller',
        name='goal_controller',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    environment_setup_node = Node(
        package='robot_control',
        executable='environment_setup',
        name='environment_setup',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    moveit = TimerAction(
        period=10.0,
        actions=[move_group_node, rviz_node, goal_controller_node, environment_setup_node]
    )

    cameras = TimerAction(
        period=15.0,
        actions=[camera_bridge]
    )

    return LaunchDescription([
        gazebo_and_controllers,
        moveit,
        cameras,
        topic_relay,
        camera_top_tf,
    ])
