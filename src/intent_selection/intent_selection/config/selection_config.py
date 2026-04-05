
VERBAL_COMMANDS = [
    "pick that up",
    "pick that up and put it in the box",
    "give me that"
]


from dataclasses import dataclass, field

@dataclass(frozen=True)
class SelectionConfig:
    eye_gaze_commands: list[str] = field(default_factory=lambda: VERBAL_COMMANDS)
    camera_source: str = 'device'  # 'device' or 'topic'
    camera_device: str = '/dev/video0'  # Used if camera_source is 'device
    image_width: int = 1280
    image_height: int = 720
    frame_rate: int = 30
    window_name: str = 'Object Selection'
    gaze_proximity_threshold: float = 50.0  # pixels