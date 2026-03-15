from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_own_detection = LaunchConfiguration('use_own_detection', default='true')
    camera_device = LaunchConfiguration('camera_device', default='/dev/video0')
    use_ros_camera = LaunchConfiguration('use_ros_camera', default='false')
    user_camera_topic = LaunchConfiguration(
        'user_camera_topic', default='/input/camera_feed/rgb/eye_camera')
    depth_topic = LaunchConfiguration('depth_topic', default='/cameras/top/depth')
    camera_info_topic = LaunchConfiguration(
        'camera_info_topic', default='/cameras/top/camera_info')
    env_image_width = LaunchConfiguration('env_image_width', default='1280')
    env_image_height = LaunchConfiguration('env_image_height', default='720')

    gaze_tracking_node = Node(
        package='gaze_tracking',
        executable='gaze_tracking_node',
        name='gaze_tracking_node',
        parameters=[{
            'camera_device': camera_device,
            'use_ros_camera': use_ros_camera,
            'user_camera_topic': user_camera_topic,
            'env_image_width': env_image_width,
            'env_image_height': env_image_height,
        }],
        output='screen'
    )

    detection_node = Node(
        package='gaze_tracking',
        executable='detection_node',
        name='gaze_detection_node',
        condition=IfCondition(use_own_detection),
        output='screen'
    )

    gaze_overlay_node = Node(
        package='gaze_tracking',
        executable='gaze_overlay_node',
        name='gaze_overlay_node',
        output='screen'
    )

    object_localizer_node = Node(
        package='gaze_tracking',
        executable='object_localizer_node',
        name='object_localizer_node',
        parameters=[{
            'depth_topic': depth_topic,
            'camera_info_topic': camera_info_topic,
        }],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_own_detection', default_value='true'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),
        DeclareLaunchArgument('use_ros_camera', default_value='false'),
        DeclareLaunchArgument('user_camera_topic',
                              default_value='/input/camera_feed/rgb/eye_camera'),
        DeclareLaunchArgument('depth_topic', default_value='/cameras/top/depth'),
        DeclareLaunchArgument('camera_info_topic',
                              default_value='/cameras/top/camera_info'),
        DeclareLaunchArgument('env_image_width', default_value='1280'),
        DeclareLaunchArgument('env_image_height', default_value='720'),
        gaze_tracking_node,
        detection_node,
        gaze_overlay_node,
        object_localizer_node,
    ])
