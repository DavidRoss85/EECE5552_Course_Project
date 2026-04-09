"""
VLA Inference Node Configuration
---------------------------------
All ROS topic strings are imported from robot_common.config.ros_config.
This file owns only VLA-specific non-topic config:
  - inference method selector
  - LeRobot model / robot / camera parameters
  - async PolicyServer parameters
  - flexible argument injection for custom lerobot flags

IMPORTANT FOR TEAMMATES:
- Update camera configs to match your setup
- Change policy_path to point to your model checkpoints
- Modify dataset_repo_id and dataset_root for your experiments
- Add custom lerobot arguments via extra_lerobot_args
"""

from dataclasses import dataclass
from enum import Enum
import os
from typing import List

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

    BASH_SCRIPT           — Executes a saved bash script directly.
                            Useful when teammate has complex setup scripts
                            with environment variables and custom logic.

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
    BASH_SCRIPT           = "bash_script"
    POLICY_SERVER_RELAY   = "policy_server_relay"
    POLICY_SERVER_DIRECT  = "policy_server_direct"


# ---------------------------------------------------------------------------
# Camera configuration templates
# ---------------------------------------------------------------------------

# Template matching teammate's current setup (3 cameras: top, side, front)
_CAMERA_CFG_3CAM = (
    f"{{ top: {{type: opencv, index_or_path: 'ros://{ROS_CFG.topic_camera_top}', "
    f"width: 640, height: 480, fps: 30 }}, "
    f"side: {{type: opencv, index_or_path: 'ros://{ROS_CFG.topic_camera_side}', "
    f"width: 640, height: 480, fps: 30 }}, "
    f"front: {{type: opencv, index_or_path: 'ros://{ROS_CFG.topic_camera_front}', "
    f"width: 640, height: 480, fps: 30 }} }}"
)

# Original configuration (with gripper cam) 
_CAMERA_CFG_WITH_GRIPPER = (
    f"{{ top: {{type: opencv, index_or_path: 'ros://{ROS_CFG.topic_camera_top}', "
    f"width: 640, height: 480, fps: 15 }}, "
    f"side: {{type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 15 }}, "
    f"gripper: {{type: opencv, index_or_path: /dev/video1, width: 640, height: 480, fps: 15 }} }}"
)

# Minimal single camera setup
_CAMERA_CFG_SINGLE = (
    f"{{ top: {{type: opencv, index_or_path: 'ros://{ROS_CFG.topic_camera_top}', "
    f"width: 640, height: 480, fps: 30 }} }}"
)


# ---------------------------------------------------------------------------
# Policy path templates
# ---------------------------------------------------------------------------

# Teammate's current model path structure
_POLICY_PATH_50K = os.path.join(
    os.path.expanduser("~"),
    "GitHub/EECE5552_Course_Project/outputs/train/"
    "smolvla_ur12e_test/checkpoints/050000/pretrained_model"
)

# Original 25K checkpoint
_POLICY_PATH_25K = os.path.join(
    os.path.expanduser("~"),
    "GitHub/EECE5552_Course_Project/outputs/train/"
    "smolvla_ur12e_gaze_with_gripper/checkpoints/025000/pretrained_model"
)

# ACT model for simulation (teammate's latest)
_POLICY_PATH_ACT_SIM = os.path.join(
    os.path.expanduser("~"),
    "GitHub/EECE5552_Course_Project/outputs/train/"
    "act_ur12e_sim/checkpoints/001000/pretrained_model"
)

# Base model fallback
_POLICY_PATH_BASE = "lerobot/smolvla_base"


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
    # TEAMMATE: Update this to match your current model checkpoint
    policy_path:        str = _POLICY_PATH_50K
    policy_device:      str = "cuda"
    lerobot_cmd:        str = "lerobot-record"      # or "lerobot-eval"
    robot_type:         str = "ur12e_ros"
    robot_id:           str = "ur12e"
    
    # ── Bash script mode settings ────────────────────────────────────────────
    # TEAMMATE: Set this to your saved script path for BASH_SCRIPT mode
    bash_script_path:   str = os.path.join(
        os.path.expanduser("~"),
        "GitHub/EECE5552_Course_Project/scripts/start-smolvla.sh"
    )
    # Script arguments that get passed to your bash script
    # The orchestrator will pass gaze coordinates as $1 and $2
    bash_script_args:   List[str] = None  # Additional args like ["--debug", "mode=sim"]
    
    # TEAMMATE: Choose camera config that matches your setup
    # Options: _CAMERA_CFG_3CAM, _CAMERA_CFG_WITH_GRIPPER, _CAMERA_CFG_SINGLE
    camera_cfg:         str = _CAMERA_CFG_3CAM
    
    # TEAMMATE: Update dataset settings for your experiments
    dataset_repo_id:    str = "frazier-z/eval_ur12e"
    dataset_root:       str = "eval_smolvla"
    dataset_fps:        int = 30    # Updated to match teammate's script
    dataset_num_episodes: int = 1
    push_to_hub:        bool = False
    
    # Default task (can be overridden by orchestrator command)
    default_task:       str = "pick up imaginary block"
    
    # ── Gaze input settings ──────────────────────────────────────────────────
    enable_gaze_input:  bool = True

    # ── Custom lerobot arguments ─────────────────────────────────────────────
    # TEAMMATE: Add any custom flags here, e.g. ["--myshirt.is=green", "--debug=true"]
    # These will be appended to the lerobot command exactly as written
    extra_lerobot_args: List[str] = None
    
    # ── Episode and timing settings ──────────────────────────────────────────
    episode_time_s:     int   = 30      # Max episode duration in seconds
    resume_dataset:     bool  = False   # --resume flag for continuing existing datasets

    # ── Async PolicyServer config (methods 2 & 3) ────────────────────────────
    policy_server_host:     str   = "127.0.0.1"
    policy_server_port:     int   = 8080
    actions_per_chunk:      int   = 50
    chunk_size_threshold:   float = 0.5

    def __post_init__(self):
        """Set default values for optional lists if not provided."""
        if self.extra_lerobot_args is None:
            # Default to empty list - no extra arguments
            object.__setattr__(self, 'extra_lerobot_args', [])
        if self.bash_script_args is None:
            # Default to empty list - no extra script arguments
            object.__setattr__(self, 'bash_script_args', [])


# ---------------------------------------------------------------------------
# Configuration presets for different use cases
# ---------------------------------------------------------------------------

# Current teammate setup (50K checkpoint, 3 cameras, 30fps)
TEAMMATE_CURRENT_CFG = VlaInferenceConfig(
    policy_path=_POLICY_PATH_50K,
    camera_cfg=_CAMERA_CFG_3CAM,
    dataset_repo_id="frazier-z/eval_ur12e",
    dataset_root="eval_smolvla",
    dataset_fps=30,
    default_task="pick up imaginary block"
)

# Gaze-enabled setup (25K checkpoint with gaze)
GAZE_ENABLED_CFG = VlaInferenceConfig(
    policy_path=_POLICY_PATH_25K,
    camera_cfg=_CAMERA_CFG_WITH_GRIPPER,
    dataset_repo_id="frazier-z/eval_ur12e_gaze_with_gripper",
    dataset_root="eval_ur12e_gaze_with_gripper",
    dataset_fps=15,
    enable_gaze_input=True,
    default_task="grab target block"
)

# ACT model for simulation (teammate's latest)
ACT_SIM_CFG = VlaInferenceConfig(
    policy_path=_POLICY_PATH_ACT_SIM,
    camera_cfg=_CAMERA_CFG_3CAM,
    dataset_repo_id="frazier-z/eval_act_ur12e_sim",
    dataset_root=os.path.join(
        os.path.expanduser("~"),
        "GitHub/EECE5552_Course_Project/eval_datasets/eval_act_ur12e_sim"
    ),
    dataset_fps=30,
    episode_time_s=120,  # 2 minutes per episode
    enable_gaze_input=False,  # ACT model doesn't use gaze
    default_task="grab target block",
    resume_dataset=True,  # Will be dynamically determined
    extra_lerobot_args=[
        "--robot.ros2_interface.gripper_joint_name="  # Empty gripper joint name
    ]
)

# Base model fallback (use HuggingFace hosted model)
BASE_MODEL_CFG = VlaInferenceConfig(
    policy_path=_POLICY_PATH_BASE,
    camera_cfg=_CAMERA_CFG_SINGLE,
    dataset_repo_id="test/eval_base",
    dataset_root="eval_base",
    dataset_fps=15,
    default_task="pick up object"
)

# Script-based execution (teammate's bash scripts)
BASH_SCRIPT_CFG = VlaInferenceConfig(
    inference_method=InferenceMethod.BASH_SCRIPT,
    bash_script_path=os.path.join(
        os.path.expanduser("~"),
        "GitHub/EECE5552_Course_Project/scripts/eval-act-sim.sh"
    ),
    bash_script_args=[],  # Additional arguments if needed
    enable_gaze_input=False,  # Script handles its own gaze logic
    default_task="grab target block"
)

# Example with custom arguments
CUSTOM_ARGS_CFG = VlaInferenceConfig(
    policy_path=_POLICY_PATH_50K,
    camera_cfg=_CAMERA_CFG_3CAM,
    extra_lerobot_args=[
        "--robot.max_episode_steps=100",
        "--policy.temperature=0.1", 
        "--dataset.video_backend=imageio",
        # Add any custom flags your teammate needs here
    ]
)

# Default configuration (use teammate's current setup)
STD_VLA_CFG = BASH_SCRIPT_CFG