from enum import Enum

USING_GAZEBO = True

# Enum for various topics:
class TopicKey(str, Enum):
    RGB_FEED            = '/input/camera_feed/rgb/'
    DEPTH_FEED          = '/input/camera_feed/depth/'
    EYE_GAZE            = '/input/eye_gaze/'
    VLA_INPUT           = '/vla/input'
    VLA_OUTPUT          = '/vla/output'
    VLA_STATUS          = '/vla/status'
    VLA_ACTION_OUTPUT   = '/vla/action_output'
    VLA_GAZE_COORDS     = '/vla/coords'
    MOVEIT_PLANNING     = '/moveit/planning'
    OBJECT_DETECTIONS   = '/intent_selection/detections'
    TEXT_COMMANDS       = '/intent_selection/text_commands'
    INTENTION_OUTPUT    = '/intent_selection/intention_output'
    # Orchestrator topics
    ORCHESTRATOR_STATE  = '/orchestrator/state'
    GRIPPER_POSITION    = '/gripper_position'
    GOAL_POSE          = '/goal_pose'
    # Camera topics for LeRobot
    CAMERAS_BASE        = '/cameras/'

from dataclasses import dataclass

# Data class for ros configurations
@dataclass(frozen=True)
class RosConfig:
    topic_full_view_rgb:        str = TopicKey.RGB_FEED + 'full_view'
    topic_full_view_depth:      str = TopicKey.DEPTH_FEED + 'full_view'
    topic_object_view_rgb:      str = TopicKey.RGB_FEED + 'object_view'
    topic_object_view_depth:    str = TopicKey.DEPTH_FEED + 'object_view'
    topic_eye_camera_rgb:       str = TopicKey.RGB_FEED + 'eye_camera'
    topic_eye_gaze:             str = TopicKey.EYE_GAZE + 'coords'
    topic_eye_gaze_calibration: str = TopicKey.EYE_GAZE + 'calibration'
    topic_vla_input:            str = TopicKey.VLA_INPUT
    topic_vla_output:           str = TopicKey.VLA_OUTPUT
    topic_vla_status:           str = TopicKey.VLA_STATUS
    topic_vla_action_output:    str = TopicKey.VLA_ACTION_OUTPUT
    topic_vla_gaze_coords:      str = TopicKey.VLA_GAZE_COORDS
    topic_moveit_planning:      str = TopicKey.MOVEIT_PLANNING
    topic_detections:           str = TopicKey.OBJECT_DETECTIONS
    topic_text_commands:        str = TopicKey.TEXT_COMMANDS
    topic_intention_output:     str = TopicKey.INTENTION_OUTPUT
    topic_orchestrator_state:   str = TopicKey.ORCHESTRATOR_STATE
    topic_gripper_position:     str = TopicKey.GRIPPER_POSITION
    topic_goal_pose:            str = TopicKey.GOAL_POSE
    # LeRobot camera topics
    topic_camera_top:           str = TopicKey.CAMERAS_BASE + 'top/image_raw'
    topic_camera_side:          str = TopicKey.CAMERAS_BASE + 'side/image_raw' 
    topic_camera_front:         str = TopicKey.CAMERAS_BASE + 'front/image_raw'
    max_messages:               int = 10
    sync_slop                       = 0.1

STD_CFG = RosConfig()