# Type defs for Ros Configurations:

from enum import Enum

USING_GAZEBO = True

# Enum for various topics:
class TopicKey(str, Enum):
    RGB_FEED = '/input/camera_feed/rgb/'
    DEPTH_FEED = '/input/camera_feed/depth/'
    EYE_GAZE = '/input/eye_gaze/'
    VLA_INPUT = '/vla/input'
    VLA_OUTPUT = '/vla/output'
    MOVEIT_PLANNING = '/moveit/planning'
    OBJECT_DETECTIONS = '/intent_selection/detections'
    TEXT_COMMANDS = '/intent_selection/text_commands'

from dataclasses import dataclass

# Data class for ros configurations
@dataclass(frozen=True)
class RosConfig:
    topic_full_view_rgb: str=TopicKey.RGB_FEED + 'full_view'
    topic_full_view_depth: str=TopicKey.DEPTH_FEED + 'full_view'
    topic_object_view_rgb: str=TopicKey.RGB_FEED + 'object_view'
    topic_object_view_depth: str=TopicKey.DEPTH_FEED + 'object_view'
    topic_eye_camera_rgb: str=TopicKey.RGB_FEED + 'eye_camera'
    topic_eye_gaze: str=TopicKey.EYE_GAZE + 'coords'
    topic_eye_gaze_calibration: str=TopicKey.EYE_GAZE + 'calibration'
    topic_vla_input: str=TopicKey.VLA_INPUT
    topic_vla_output: str=TopicKey.VLA_OUTPUT
    topic_moveit_planning: str=TopicKey.MOVEIT_PLANNING
    topic_detections: str=TopicKey.OBJECT_DETECTIONS
    topic_text_commands: str=TopicKey.TEXT_COMMANDS
    max_messages: int = 10
    sync_slop = 0.1

STD_CFG = RosConfig()
