
# YOLO Classes - Order specific. Maps YOLO class IDs to names
YOLO_CLASSES: tuple[str, ...] = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush"
)


from enum import Enum
from typing import FrozenSet
from dataclasses import dataclass, field
import logging

# Constants
DEFAULT_CONFIDENCE_THRESHOLD = 0.8 # Default confidence threshold for YOLO detections

# Setup logger
logger = logging.getLogger(__name__)

# Detection Filter Modes:
class DetectionFilterMode(str, Enum):
    ALL = 'all' # No filtering
    ALLOW = 'allow' # Only allow specified classes
    REJECT = 'reject'   # Reject specified classes

# Yolo Models:
class YoloModel(str, Enum):
    NANO = 'yolov8n.pt'
    SMALL = 'yolov8s.pt'
    MEDIUM = 'yolov8m.pt'

# Compute Preferences:
class ComputePreference(Enum):
    CPU_ONLY = "cpu_only"
    ACCELERATE_IF_AVAILABLE = "accelerate_if_available"
    MAX_THROUGHPUT = "max_throughput"
    THROTTLED = "throttled"



# YoloConfig Dataclass:
@dataclass(frozen=True)
class YoloConfig:
    model: YoloModel = YoloModel.NANO
    compute_preference: ComputePreference = ComputePreference.CPU_ONLY
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD

    filter_mode: DetectionFilterMode = DetectionFilterMode.ALL
    target_classes: FrozenSet[str] = field(default_factory=frozenset)   # Only used in ALLOW mode (Default: empty set)
    ignore_classes: FrozenSet[str] = field(default_factory=frozenset)   # Only used in REJECT mode (Default: empty set)

    # Normalize class names to lowercase and strip whitespace
    def _normalize_classes(self, classes: FrozenSet[str], label: str) -> FrozenSet[str]:
        normalized = set()
        changes = {}

        for c in classes:
            fixed = c.strip().lower()
            normalized.add(fixed)

            if fixed != c:
                changes[c] = fixed

        # Warn user about changes:
        if changes:
            formatted = ", ".join(
                f"'{old}' → '{new}'"
                for old, new in sorted(changes.items())
            )
            logger.warning(
                "Normalized YOLO %s class names: %s",
                label,
                formatted
            )

        return frozenset(normalized)

    # Post init to validate and adjust values
    def __post_init__(self):
        ct = self.confidence_threshold

        # Clamp confidence threshold to a valid range
        if not (0.0 < ct <= 1.0):
            logger.warning(
                "Invalid YOLO confidence_threshold=%s. "
                "Clamping to default %s.",
                ct, DEFAULT_CONFIDENCE_THRESHOLD
            )   # Warn user before clamping

            # Use object.__setattr__ to bypass the frozen dataclass
            object.__setattr__(self, "confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)


        # Ensure that the target_classes and ignore_classes are valid

        # Normalize class names:
        
        # Targets
        object.__setattr__(
            self,
            "target_classes",
            self._normalize_classes(self.target_classes, "target")
        )

        # Ignores
        object.__setattr__(
            self,
            "ignore_classes",
            self._normalize_classes(self.ignore_classes, "ignore")
        )

        # We explicitly hard crash from here onward to avoid silent bugs and assure user intention...
        
        # Validate class names
        invalid = (
            self.target_classes | self.ignore_classes
        ) - set(YOLO_CLASSES)

        if invalid:
            raise ValueError(
                f"Unknown YOLO class names: {sorted(invalid)}"
            )
        
        # Allow mode (Must have at least one class to allow):
        if self.filter_mode == DetectionFilterMode.ALLOW and not self.target_classes:
            raise ValueError("ALLOW mode requires target_classes")

        # Reject mode (Must have at least one class to reject):
        if self.filter_mode == DetectionFilterMode.REJECT and not self.ignore_classes:
            raise ValueError("REJECT mode requires ignore_classes")
        