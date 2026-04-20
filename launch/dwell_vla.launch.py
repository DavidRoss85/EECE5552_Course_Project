from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # ── Args ──────────────────────────────────────────────────────────
        DeclareLaunchArgument('scene_device',  default_value='/dev/video2',
                              description='USB device for the scene camera (v4l2)'),
        DeclareLaunchArgument('eye_cam_index', default_value='0',
                              description='Integer index for EyeGestures v2 eye camera'),
        DeclareLaunchArgument('colors',        default_value='["red","blue","yellow"]',
                              description='Colors for detection_node to track'),
        DeclareLaunchArgument('dwell_time',    default_value='2.0',
                              description='Seconds of gaze hold before VLA fires'),
        DeclareLaunchArgument('cooldown_time', default_value='5.0',
                              description='Seconds before the same object can re-trigger'),
        DeclareLaunchArgument('script_path',
                              default_value='/home/zackary-frazier/GitHub/EECE5552_Course_Project/scripts/ur12e/start-act.sh',
                              description='Absolute path to start-act.sh'),

        # ── Scene camera → /cameras/front/image_raw ───────────────────────
        Node(
            package='v4l2_camera',
            executable='v4l2_camera_node',
            name='scene_camera',
            output='screen',
            parameters=[{
                'video_device': LaunchConfiguration('scene_device'),
                'image_size':   [640, 480],
            }],
            remappings=[('image_raw', '/cameras/front/image_raw')],
        ),

        # ── vla_detector_multi → /vla/coords + /vla/detections + /vla/preview
        Node(
            package='perception',
            executable='vla_detector_multi',
            name='vla_detector_multi',
            output='screen',
            parameters=[{
                'camera_source': 'topic',
                'camera_topic':  '/cameras/front/image_raw',
                'colors':        LaunchConfiguration('colors'),
                'display':       False,
            }],
        ),

        # ── Dwell VLA node (EyeGestures v2 + UI + VLA trigger) ───────────
        Node(
            package='user_interface',
            executable='dwell_vla_node',
            name='dwell_vla_node',
            output='screen',
            parameters=[{
                'script_path':   LaunchConfiguration('script_path'),
                'dwell_time':    LaunchConfiguration('dwell_time'),
                'cooldown_time': LaunchConfiguration('cooldown_time'),
                'eye_cam_index': LaunchConfiguration('eye_cam_index'),
            }],
        ),
    ])
