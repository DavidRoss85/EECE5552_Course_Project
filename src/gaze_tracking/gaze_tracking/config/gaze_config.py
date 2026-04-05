from enum import Enum
from dataclasses import dataclass

@dataclass(frozen=True)
class GazeConfig:
    # Camera source config
    input_mode: str = 'device'  # 'device', 'topic', or 'dummy'
    camera_device: str = '/dev/video0'  # for 'device' mode; ignored otherwise
    env_width: int = 600 #1280
    env_height: int = 500 # 720
    calib_points: int = 25
    show_feed: bool = True
    show_fullscreen: bool = False
    mirror_x_axis: bool = False
    use_calibration_map: bool = False
    test_mode: bool = False  # skip EyeGestures, publish dummy gaze at center
