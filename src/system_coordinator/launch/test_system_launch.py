#!/usr/bin/env python3
"""
System Test Launch File
-----------------------
Launches the system in test mode with synthetic data generators.
This allows testing the intent selection pipeline without physical hardware.

Launches:
- Intent Selection Tester (generates synthetic gaze, detections, voice commands)
- Intent Selection GUI (visualizes the system and user interactions)  
- System Orchestrator (coordinates the pipeline, but VLA commands will timeout)

Note: This test setup does not include VLA inference - the orchestrator will 
receive commands but they will timeout since no VLA node responds. This is 
useful for testing the intent selection and coordination logic.

Usage:
  ros2 launch system_coordinator test_system_launch.py
  ros2 launch system_coordinator test_system_launch.py config_file:=config/test_config.yaml
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition


def generate_launch_description():
    
    # ──────────────────────────────────────────────────────────────────────
    # Launch Arguments for Test Mode
    # ──────────────────────────────────────────────────────────────────────
    
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value='config/test_config.yaml',  # Relative to workspace root
        description='Path to test YAML configuration file (relative to workspace root or absolute path)'
    )
    
    enable_tester_arg = DeclareLaunchArgument(
        'enable_tester', default_value='true',
        description='Enable intent selection tester node (synthetic data)'
    )
    
    enable_gui_arg = DeclareLaunchArgument(
        'enable_gui', default_value='true',
        description='Enable intent selection GUI'
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Test Node Definitions
    # ──────────────────────────────────────────────────────────────────────
    
    def launch_setup(context, *args, **kwargs):
        config_file = LaunchConfiguration('config_file')
        
        nodes = []
        
        # ── Synthetic Data Generator ──────────────────────────────────────────
        tester_node = Node(
            package='intent_selection',
            executable='test_intent_selection_node',
            name='intent_selection_tester',
            parameters=[config_file, {
                # Synthetic data settings
                'image_width': 1280,
                'image_height': 720,
                'gaze_speed': 0.5,
                'command_interval': 10.0,
                'publish_camera': True,
                
                # ROS topics
                'gaze_topic': '/input/eye_gaze/coords',
                'calibration_topic': '/input/eye_gaze/calibration',
                'detections_topic': '/intent_selection/detections',
                'voice_commands_topic': '/intent_selection/text_commands',
                'camera_topic': '/input/camera_feed/rgb/full_view',
                'max_messages': 10,
            }],
            condition=IfCondition(LaunchConfiguration('enable_tester')),
            output='screen'
        )
        
        # ── Intent Selection GUI (for visualization) ──────────────────────────
        intent_node = Node(
            package='intent_selection',
            executable='intent_selection_node',
            name='intent_selection_node',
            parameters=[config_file, {
                # Use topic input since tester publishes camera feed
                'camera_source': 'topic',
                'camera_device': '/dev/video2',  # Unused in topic mode
                'image_width': 1280,
                'image_height': 720,
                'frame_rate': 30,
                
                # Display settings  
                'display_fullscreen': False,
                'window_width': 800,
                'window_height': 600,
                'gaze_proximity_threshold': 50.0,
                
                # ROS topics (matching tester outputs)
                'camera_topic': '/input/camera_feed/rgb/full_view',
                'gaze_topic': '/input/eye_gaze/coords',
                'calibration_topic': '/input/eye_gaze/calibration',
                'detections_topic': '/intent_selection/detections',
                'voice_commands_topic': '/intent_selection/text_commands',
                'vla_input_topic': '/vla/input',
                'intention_output_topic': '/intent_selection/intention_output',
                'max_messages': 10,
            }],
            condition=IfCondition(LaunchConfiguration('enable_gui')),
            output='screen'
        )
        
        # ── System Orchestrator (test mode) ───────────────────────────────────
        orchestrator_node = Node(
            package='system_coordinator',
            executable='orchestrator_node',
            name='orchestrator_node',
            parameters=[config_file, {
                # Fast timing for testing
                'auto_handoff': True,
                'handoff_timeout_s': 5.0,
                'home_timeout_s': 3.0,
                
                # Test gripper settings
                'gripper_open_pos': 1.0,
                'gripper_closed_pos': 0.0,
                
                # ROS topics
                'intention_topic': '/intent_selection/intention_output',
                'vla_status_topic': '/vla/status',
                'vla_input_topic': '/vla/input',
                'orchestrator_state_topic': '/orchestrator/state',
                'gripper_topic': '/gripper_position',
                'goal_pose_topic': '/goal_pose',
                'max_messages': 10,
            }],
            output='screen'
        )
        
        # Add all nodes
        nodes.extend([
            tester_node,
            intent_node,
            orchestrator_node,
        ])
        
        return nodes
    
    # ──────────────────────────────────────────────────────────────────────
    # Launch Description
    # ──────────────────────────────────────────────────────────────────────
    
    return LaunchDescription([
        config_file_arg,
        enable_tester_arg,
        enable_gui_arg,
        
        # Use OpaqueFunction to defer node creation until launch time
        OpaqueFunction(function=launch_setup)
    ])