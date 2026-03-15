import numpy as np
import pytest


def test_yolo_result_to_detected_item_fields():
    xyxy = [10, 20, 110, 120]
    conf = 0.87
    x1, y1, x2, y2 = [int(v) for v in xyxy]
    assert x1 == 10
    assert y1 == 20
    assert x2 == 110
    assert y2 == 120
    assert abs(conf - 0.87) < 1e-6


def test_xywh_from_xyxy():
    x1, y1, x2, y2 = 10, 20, 110, 120
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w // 2
    cy = y1 + h // 2
    assert w == 100
    assert h == 100
    assert cx == 60
    assert cy == 70
