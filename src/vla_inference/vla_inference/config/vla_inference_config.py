"""
VLA Inference Node Configuration
---------------------------------
All ROS topic strings are imported from robot_common.config.ros_config.
This file owns only VLA-specific non-topic config:
  - inference method selector
  - LeRobot model / robot / camera parameters
  - async PolicyServer parameters
"""

from dataclasses import dataclass
from enum import Enum
import os

from robot_common.config.ros_config import STD_CFG as ROS_CFG


# ---------------------------------------------------------------------------
# Inference method selector
# ---------------------------------------------------------------------------

class InferenceMethod(str, Enum):
    """
    Controls how the VLA inference node invokes LeRobot.

    SUBPROCESS            — Launches lerobot-record (or lerobot-eval) as a
                            child process and waits for it to exit.
                            Simple, no API integration required.

    POLICY_SERVER_RELAY   — Spins up a PolicyServer, connects a relay
                            RobotClient that captures action vectors and
                            republishes them to /vla/action_output.
                            A downstream controller applies them to hardware.

    POLICY_SERVER_DIRECT  — Spins up a PolicyServer and a standard
                            RobotClient that talks directly to the UR
                            hardware. The node monitors completion and
                            publishes a DONE status when the episode ends.
    """
    SUBPROCESS            = "subprocess"
    POLICY_SERVER_RELAY   = "policy_server_relay"
    POLICY_SERVER_DIRECT  = "policy_server_direct"


# ---------------------------------------------------------------------------
# LeRobot / camera defaults
# ---------------------------------------------------------------------------

_DEFAULT_CAMERA_CFG = (
    "{ top: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', "
    "width: 640, height: 480, fps: 15 }, "
    "side: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 15 }, "
    "gripper: {type: opencv, index_or_path: /dev/video1, width: 640, height: 480, fps: 15 } }"
)

_DEFAULT_POLICY_PATH = os.path.join(
    os.path.expanduser("~"),
    "GitHub/EECE5552_Course_Project/outputs/train/"
    "smolvla_ur12e_gaze_with_gripper/checkpoints/025000/pretrained_model",
)


# ---------------------------------------------------------------------------
# VLA inference config — topics pulled from ROS_CFG, everything else here
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VlaInferenceConfig:

    # ── ROS topics (sourced from robot_common) ───────────────────────────────
    topic_command_in:   str = ROS_CFG.topic_vla_input
    topic_status_out:   str = ROS_CFG.topic_vla_status
    topic_action_out:   str = ROS_CFG.topic_vla_action_output
    topic_gaze_coords:  str = ROS_CFG.topic_vla_gaze_coords
    max_messages:       int = ROS_CFG.max_messages

    # ── Inference method ─────────────────────────────────────────────────────
    inference_method:   str = InferenceMethod.SUBPROCESS

    # ── LeRobot / model config ───────────────────────────────────────────────
    policy_path:        str = _DEFAULT_POLICY_PATH
    policy_device:      str = "cuda"
    lerobot_cmd:        str = "lerobot-record"      # or "lerobot-eval"
    robot_type:         str = "ur12e_ros"
    robot_id:           str = "ur12e"
    camera_cfg:         str = _DEFAULT_CAMERA_CFG
    dataset_repo_id:    str = "frazier-z/eval_ur12e_gaze_with_gripper"
    dataset_root:       str = "eval_ur12e_gaze_with_gripper"
    dataset_fps:        int = 15
    dataset_num_episodes: int = 1
    push_to_hub:        bool = False
    enable_gaze_input:  bool = True

    # ── Async PolicyServer config (methods 2 & 3) ────────────────────────────
    policy_server_host:     str   = "127.0.0.1"
    policy_server_port:     int   = 8080
    actions_per_chunk:      int   = 50
    chunk_size_threshold:   float = 0.5
    episode_time_s:         int   = 30


STD_VLA_CFG = VlaInferenceConfig()