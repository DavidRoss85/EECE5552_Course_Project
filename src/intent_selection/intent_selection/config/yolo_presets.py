
from intent_selection.config.yolo_config import(
    YoloConfig,
    DetectionFilterMode,
    YoloModel,
    ComputePreference
)

#Intend to build a factory later:


DEFAULT_YOLO_CONFIG = YoloConfig(
    model=YoloModel.MEDIUM,
    compute_preference=ComputePreference.MAX_THROUGHPUT,
    confidence_threshold=0.8,
    filter_mode=DetectionFilterMode.ALL,
)

IGNORE_PEOPLE = YoloConfig(
    model=YoloModel.MEDIUM,
    compute_preference=ComputePreference.MAX_THROUGHPUT,
    confidence_threshold=0.8,
    filter_mode=DetectionFilterMode.REJECT,
    ignore_classes={"person"},
)