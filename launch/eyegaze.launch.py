from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_own_detection = LaunchConfiguration('use_own_detection', default='true')
    camera_device = LaunchConfiguration('camera_device', default='/dev/video0')
    depth_topic = LaunchConfiguration('depth_topic', default='/cameras/top/depth')
    camera_info_topic = LaunchConfiguration(
        'camera_info_topic', default='/cameras/top/camera_info')
    env_image_width = LaunchConfiguration('env_image_width', default='1280')
    env_image_height = LaunchConfiguration('env_image_height', default='720')
    test_mode = LaunchConfiguration('test_mode', default='false')
    env_rgb_topic = LaunchConfiguration(
        'env_rgb_topic', default='/input/camera_feed/rgb/full_view')

    gaze_tracking_node = Node(
        package='gaze_tracking',
        executable='gaze_tracking_node',
        name='gaze_tracking_node',
        parameters=[{
            'camera_device': camera_device,
            'env_image_width': env_image_width,
            'env_image_height': env_image_height,
            'test_mode': test_mode,
        }],
        output='screen'
    )

    detection_node = Node(
        package='gaze_tracking',
        executable='detection_node',
        name='gaze_detection_node',
        condition=IfCondition(use_own_detection),
        parameters=[{'rgb_topic': env_rgb_topic}],
        output='screen'
    )

    gaze_overlay_node = Node(
        package='gaze_tracking',
        executable='gaze_overlay_node',
        name='gaze_overlay_node',
        parameters=[{'rgb_topic': env_rgb_topic}],
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

    # ── TODO: voice confirmation node ────────────────────────────────────────
    # Publishes recognized speech to /intent_selection/text_commands (std_msgs/String)
    # Trigger words ('select', 'grab', 'yes', 'confirm', 'take') confirm gaze selection
    # without requiring a full dwell.  Wire in here once the speech node is ready:
    #
    # voice_confirmation_node = Node(
    #     package='intent_selection',
    #     executable='voice_confirmation_node',
    #     name='voice_confirmation_node',
    #     output='screen',
    # )
    # ── TODO: robot orientation node ─────────────────────────────────────────
    # Reads selected pose from /gaze_tracking/selected_point and adjusts
    # end-effector orientation to face the object before executing the move.
    # ─────────────────────────────────────────────────────────────────────────

    return LaunchDescription([
        DeclareLaunchArgument('use_own_detection', default_value='true'),
        DeclareLaunchArgument('camera_device', default_value='/dev/video0'),
        DeclareLaunchArgument('depth_topic', default_value='/cameras/top/depth'),
        DeclareLaunchArgument('camera_info_topic',
                              default_value='/cameras/top/camera_info'),
        DeclareLaunchArgument('env_image_width', default_value='1280'),
        DeclareLaunchArgument('env_image_height', default_value='720'),
        DeclareLaunchArgument('test_mode', default_value='false'),
        DeclareLaunchArgument('env_rgb_topic',
                              default_value='/input/camera_feed/rgb/full_view'),
        gaze_tracking_node,
        detection_node,
        gaze_overlay_node,
        object_localizer_node,
        # voice_confirmation_node,   # uncomment when ready
    ])
