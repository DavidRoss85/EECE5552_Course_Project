#!/usr/bin/env python3
"""
System Launch File
------------------
Launches the complete robot vision-grasp system:
- Gaze tracking node
- Object detection node  
- Voice command node
- Intent selection node
- System orchestrator node
- VLA inference node

All parameters are loaded from a YAML configuration file.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition, UnlessCondition
import os


def generate_launch_description():
    
    # ──────────────────────────────────────────────────────────────────────
    # Launch Arguments 
    # ──────────────────────────────────────────────────────────────────────
    
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value='config/system_config.yaml',  # Relative to workspace root
        description='Path to YAML configuration file (relative to workspace root or absolute path)'
    )
    
    # Individual node enable/disable flags
    enable_gaze_arg = DeclareLaunchArgument(
        'enable_gaze', default_value='true',
        description='Enable gaze tracking node'
    )
    
    enable_detection_arg = DeclareLaunchArgument(
        'enable_detection', default_value='true',
        description='Enable object detection node'
    )
    
    enable_voice_arg = DeclareLaunchArgument(
        'enable_voice', default_value='true',
        description='Enable voice command node'
    )
    
    enable_intent_arg = DeclareLaunchArgument(
        'enable_intent', default_value='true',
        description='Enable intent selection node'
    )
    
    enable_orchestrator_arg = DeclareLaunchArgument(
        'enable_orchestrator', default_value='true',
        description='Enable system orchestrator node'
    )
    
    enable_vla_arg = DeclareLaunchArgument(
        'enable_vla', default_value='true',
        description='Enable VLA inference node'
    )
    
    # Debug and test modes
    test_mode_arg = DeclareLaunchArgument(
        'test_mode', default_value='false',
        description='Enable test mode (synthetic data instead of hardware)'
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Node Definitions
    # ──────────────────────────────────────────────────────────────────────
    
    def launch_setup(context, *args, **kwargs):
        config_file = LaunchConfiguration('config_file')
        
        nodes = []
        
        # ── Gaze Tracking Node ────────────────────────────────────────────
        gaze_node = Node(
            package='gaze_tracking',
            executable='gaze_tracking_node',
            name='gaze_tracking_node',
            parameters=[config_file, {
                # Core functionality
                'input_mode': LaunchConfiguration('gaze_input_mode', default='device'),
                'camera_device': LaunchConfiguration('gaze_camera_device', default='/dev/video0'),
                'env_image_width': LaunchConfiguration('gaze_env_width', default=600),
                'env_image_height': LaunchConfiguration('gaze_env_height', default=500),
                'calib_points': LaunchConfiguration('gaze_calib_points', default=25),
                'test_mode': LaunchConfiguration('gaze_test_mode', default='false'),
                
                # Display settings
                'show_feed': LaunchConfiguration('gaze_show_feed', default='true'),
                'show_fullscreen': LaunchConfiguration('gaze_show_fullscreen', default='false'),
                'mirror_x': LaunchConfiguration('gaze_mirror_x', default='false'),
                'use_calib_map': LaunchConfiguration('gaze_use_calib_map', default='false'),
                
                # ROS topics
                'eye_gaze_topic': LaunchConfiguration('topic_eye_gaze', default='/input/eye_gaze/coords'),
                'eye_gaze_calibration_topic': LaunchConfiguration('topic_eye_gaze_calibration', default='/input/eye_gaze/calibration'),
                'max_ros_messages': LaunchConfiguration('max_ros_messages', default=10),
            }],
            condition=IfCondition(LaunchConfiguration('enable_gaze')),
            output='screen'
        )
        
        # ── Object Detection Node ──────────────────────────────────────────
        detection_node = Node(
            package='perception',
            executable='detection_node',
            name='detection_node',
            parameters=[config_file, {
                # YOLO model settings
                'yolo_model': LaunchConfiguration('yolo_model', default='yolov8m.pt'),
                'confidence_threshold': LaunchConfiguration('yolo_confidence', default=0.8),
                'compute_preference': LaunchConfiguration('yolo_compute', default='max_throughput'),
                'filter_mode': LaunchConfiguration('yolo_filter_mode', default='all'),
                
                # Display settings
                'show_feed': LaunchConfiguration('detection_show_feed', default='false'),
                'line_thickness': LaunchConfiguration('detection_line_thickness', default=2),
                'font_scale': LaunchConfiguration('detection_font_scale', default=0.5),
                
                # ROS topics
                'camera_topic': LaunchConfiguration('topic_object_view_rgb', default='/input/camera_feed/rgb/object_view'),
                'detections_topic': LaunchConfiguration('topic_detections', default='/intent_selection/detections'),
                'max_messages': LaunchConfiguration('max_ros_messages', default=10),
            }],
            condition=IfCondition(LaunchConfiguration('enable_detection')),
            output='screen'
        )
        
        # ── Voice Command Node ──────────────────────────────────────────────
        voice_node = Node(
            package='voice_command',
            executable='voice_command_node',
            name='voice_command_node',
            parameters=[config_file, {
                # Voice processing settings
                'use_local_whisper': LaunchConfiguration('voice_use_local_whisper', default='true'),
                'local_whisper_model': LaunchConfiguration('voice_whisper_model', default='base.en'),
                'openai_api_key': LaunchConfiguration('voice_openai_key', default=''),
                'llm_parse': LaunchConfiguration('voice_llm_parse', default='false'),
                'llm_model': LaunchConfiguration('voice_llm_model', default='gpt-4o-mini'),
                
                # ROS topics
                'output_topic': LaunchConfiguration('topic_text_commands', default='/intent_selection/text_commands'),
                'max_messages': LaunchConfiguration('max_ros_messages', default=10),
            }],
            condition=IfCondition(LaunchConfiguration('enable_voice')),
            output='screen'
        )
        
        # ── Intent Selection Node ───────────────────────────────────────────
        intent_node = Node(
            package='intent_selection',
            executable='intent_selection_node',
            name='intent_selection_node',
            parameters=[config_file, {
                # Camera configuration
                'camera_source': LaunchConfiguration('intent_camera_source', default='device'),
                'camera_device': LaunchConfiguration('intent_camera_device', default='/dev/video1'),
                'image_width': LaunchConfiguration('intent_image_width', default=600),
                'image_height': LaunchConfiguration('intent_image_height', default=500),
                'frame_rate': LaunchConfiguration('intent_frame_rate', default=30),
                
                # Display settings
                'display_fullscreen': LaunchConfiguration('intent_display_fullscreen', default='false'),
                'window_width': LaunchConfiguration('intent_window_width', default=600),
                'window_height': LaunchConfiguration('intent_window_height', default=500),
                'gaze_proximity_threshold': LaunchConfiguration('intent_proximity_threshold', default=50.0),
                
                # ROS topics
                'camera_topic': LaunchConfiguration('topic_full_view_rgb', default='/input/camera_feed/rgb/full_view'),
                'gaze_topic': LaunchConfiguration('topic_eye_gaze', default='/input/eye_gaze/coords'),
                'calibration_topic': LaunchConfiguration('topic_eye_gaze_calibration', default='/input/eye_gaze/calibration'),
                'detections_topic': LaunchConfiguration('topic_detections', default='/intent_selection/detections'),
                'voice_commands_topic': LaunchConfiguration('topic_text_commands', default='/intent_selection/text_commands'),
                'vla_input_topic': LaunchConfiguration('topic_vla_input', default='/vla/input'),
                'intention_output_topic': LaunchConfiguration('topic_intention_output', default='/intent_selection/intention_output'),
                'max_messages': LaunchConfiguration('max_ros_messages', default=10),
            }],
            condition=IfCondition(LaunchConfiguration('enable_intent')),
            output='screen'
        )
        
        # ── System Orchestrator Node ────────────────────────────────────────
        orchestrator_node = Node(
            package='system_coordinator',
            executable='orchestrator_node',
            name='orchestrator_node',
            parameters=[config_file, {
                # Timing parameters
                'auto_handoff': LaunchConfiguration('orchestrator_auto_handoff', default='true'),
                'handoff_timeout_s': LaunchConfiguration('orchestrator_handoff_timeout', default=30.0),
                'home_timeout_s': LaunchConfiguration('orchestrator_home_timeout', default=15.0),
                
                # Gripper settings
                'gripper_open_pos': LaunchConfiguration('orchestrator_gripper_open', default=1.0),
                'gripper_closed_pos': LaunchConfiguration('orchestrator_gripper_closed', default=0.0),
                
                # ROS topics
                'intention_topic': LaunchConfiguration('topic_intention_output', default='/intent_selection/intention_output'),
                'vla_status_topic': LaunchConfiguration('topic_vla_status', default='/vla/status'),
                'vla_input_topic': LaunchConfiguration('topic_vla_input', default='/vla/input'),
                'orchestrator_state_topic': LaunchConfiguration('topic_orchestrator_state', default='/orchestrator/state'),
                'gripper_topic': LaunchConfiguration('topic_gripper_position', default='/gripper_position'),
                'goal_pose_topic': LaunchConfiguration('topic_goal_pose', default='/goal_pose'),
                'max_messages': LaunchConfiguration('max_ros_messages', default=10),
            }],
            condition=IfCondition(LaunchConfiguration('enable_orchestrator')),
            output='screen'
        )
        
        # ── VLA Inference Node ───────────────────────────────────────────────
        vla_params = {
                # Inference method selection
                'inference_method': LaunchConfiguration('vla_inference_method', default='bash_script'),
                
                # Model and policy settings
                'policy_path': LaunchConfiguration('vla_policy_path', default='lerobot/smolvla_base'),
                'policy_device': LaunchConfiguration('vla_policy_device', default='cuda'),
                'robot_type': LaunchConfiguration('vla_robot_type', default='ur12e_ros'),
                'robot_id': LaunchConfiguration('vla_robot_id', default='ur12e'),
                
                # LeRobot command settings (for subprocess mode)
                'lerobot_cmd': LaunchConfiguration('vla_lerobot_cmd', default='lerobot-record'),
                'camera_cfg': LaunchConfiguration('vla_camera_cfg', default=''),  # Complex YAML string
                
                # Dataset settings
                'dataset_repo_id': LaunchConfiguration('vla_dataset_repo_id', default='test/eval_dataset'),
                'dataset_root': LaunchConfiguration('vla_dataset_root', default='eval_dataset'),
                'dataset_fps': LaunchConfiguration('vla_dataset_fps', default=30),
                'dataset_num_episodes': LaunchConfiguration('vla_dataset_num_episodes', default=1),
                'push_to_hub': LaunchConfiguration('vla_push_to_hub', default='false'),
                'resume_dataset': LaunchConfiguration('vla_resume_dataset', default='false'),
                
                # bash_script_args / extra_lerobot_args: never pass from launch (string '' vs string[]).
                # Optional script path: only override YAML when CLI sets a non-empty vla_bash_script_path.
                
                # Episode settings
                'episode_time_s': LaunchConfiguration('vla_episode_time_s', default=30),
                'enable_gaze_input': LaunchConfiguration('vla_enable_gaze', default='true'),
                'default_task': LaunchConfiguration('vla_default_task', default='pick up imaginary block'),
                
                # PolicyServer settings (for server modes)
                'policy_server_host': LaunchConfiguration('vla_server_host', default='127.0.0.1'),
                'policy_server_port': LaunchConfiguration('vla_server_port', default=8080),
                'actions_per_chunk': LaunchConfiguration('vla_actions_per_chunk', default=50),
                'chunk_size_threshold': LaunchConfiguration('vla_chunk_threshold', default=0.5),
                
                # ROS topics
                'command_topic': LaunchConfiguration('topic_vla_input', default='/vla/input'),
                'status_topic': LaunchConfiguration('topic_vla_status', default='/vla/status'),
                'action_output_topic': LaunchConfiguration('topic_vla_action_output', default='/vla/action_output'),
                'gaze_coords_topic': LaunchConfiguration('topic_vla_gaze_coords', default='/vla/coords'),
                'max_messages': LaunchConfiguration('max_ros_messages', default=10),
        }
        vla_bash_path = LaunchConfiguration('vla_bash_script_path', default='').perform(context)
        if vla_bash_path.strip():
            vla_params['bash_script_path'] = vla_bash_path

        vla_node = Node(
            package='vla_inference',
            executable='vla_inference_node',
            name='vla_inference_node',
            parameters=[config_file, vla_params],
            condition=IfCondition(LaunchConfiguration('enable_vla')),
            output='screen'
        )
        
        # ── Add all nodes ─────────────────────────────────────────────────────
        nodes.extend([
            gaze_node,
            detection_node, 
            voice_node,
            intent_node,
            orchestrator_node,
            vla_node
        ])
        
        return nodes
    
    # ──────────────────────────────────────────────────────────────────────
    # Launch Description
    # ──────────────────────────────────────────────────────────────────────
    
    return LaunchDescription([
        config_file_arg,
        enable_gaze_arg,
        enable_detection_arg,
        enable_voice_arg,
        enable_intent_arg,
        enable_orchestrator_arg,
        enable_vla_arg,
        test_mode_arg,
        
        # Use OpaqueFunction to defer node creation until launch time
        OpaqueFunction(function=launch_setup)
    ])
