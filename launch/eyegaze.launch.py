from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # ── Launch arguments ──────────────────────────────────────────────
        DeclareLaunchArgument('test_mode',     default_value='false',
                              description='Skip EyeGestures, publish dummy gaze'),
        DeclareLaunchArgument('camera_source', default_value='topic',
                              description='"topic" or "usb"'),
        DeclareLaunchArgument('camera_topic',
                              default_value='/input/camera_feed/rgb/full_view',
                              description='ROS image topic (camera_source=topic only)'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0',
                              description='USB device path or index (camera_source=usb only)'),
        DeclareLaunchArgument('use_depth',     default_value='false',
                              description='Enable depth backprojection and arm motion'),

        # ── gaze_tracking package ─────────────────────────────────────────
        Node(
            package='gaze_tracking',
            executable='gaze_tracking_node',
            name='gaze_tracking_node',
            output='screen',
            parameters=[{
                'test_mode':        LaunchConfiguration('test_mode'),
                'camera_device':    LaunchConfiguration('camera_device'),
                'env_image_width':  1280,
                'env_image_height': 720,
                'calib_points':     25,
            }],
        ),

        # ── perception package ────────────────────────────────────────────
        Node(
            package='perception',
            executable='detection_node',
            name='detection_node',
            output='screen',
            parameters=[{
                'camera_source': LaunchConfiguration('camera_source'),
                'camera_topic':  LaunchConfiguration('camera_topic'),
                'camera_device': LaunchConfiguration('camera_device'),
                'image_width':   1280,
                'image_height':  720,
            }],
        ),

        Node(
            package='perception',
            executable='object_localizer_node',
            name='object_localizer_node',
            output='screen',
            parameters=[{
                'use_depth': LaunchConfiguration('use_depth'),
            }],
        ),

        # ── user_interface package ────────────────────────────────────────
        Node(
            package='user_interface',
            executable='gaze_overlay_node',
            name='gaze_overlay_node',
            output='screen',
            parameters=[{
                'display_width':  1920,
                'display_height': 1080,
            }],
        ),

        # ── robot_control — only when depth/arm mode enabled ──────────────
        # NOTE: goal_controller blocks on wait_for_server() for MoveIt.
        # Do NOT set use_depth:=true unless sim.launch.py is already running.
        Node(
            package='robot_control',
            executable='goal_controller',
            name='goal_controller',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_depth')),
        ),
    ])
