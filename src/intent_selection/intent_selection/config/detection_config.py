#OpenCV
DEFAULT_IMAGE_ENCODING = 'passthrough'#'bgr8'  # OpenCV uses BGR format

# Default values:
DEFAULT_FEED_SHOW = False
DEFAULT_SHOULD_PUBLISH = True
DEFAULT_LINE_THICKNESS = 2
DEFAULT_FONT_SCALE = 0.5
DEFAULT_BGR_FONT_COLOR = (0,255,0)
DEFAULT_BGR_BOX_COLOR = (255,0,0)


from dataclasses import dataclass

@dataclass(frozen=True)
class DetectionConfig:
    show_feed: bool = DEFAULT_FEED_SHOW
    should_publish: bool = DEFAULT_SHOULD_PUBLISH
    line_thickness: int = DEFAULT_LINE_THICKNESS
    font_scale: float = DEFAULT_FONT_SCALE
    bgr_font_color: tuple = DEFAULT_BGR_FONT_COLOR
    bgr_box_color: tuple = DEFAULT_BGR_BOX_COLOR
    image_encoding: str = DEFAULT_IMAGE_ENCODING