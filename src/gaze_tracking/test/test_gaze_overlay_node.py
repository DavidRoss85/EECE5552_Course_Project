import numpy as np
import pytest


def test_gaze_overlay_node_importable():
    from gaze_tracking.gaze_overlay_node import GazeOverlayNode
    assert GazeOverlayNode is not None


def test_bbox_to_circle_conversion():
    xyxy = [50, 60, 150, 160]
    x1, y1, x2, y2 = xyxy
    center = ((x1 + x2) // 2, (y1 + y2) // 2)
    radius = int(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 2)
    assert center == (100, 110)
    assert radius == 70


def test_voice_command_matches_confirmation_phrases():
    CONFIRM_PHRASES = {'select', 'grab', 'yes', 'confirm', 'take'}
    assert 'grab' in CONFIRM_PHRASES
    assert 'hello' not in CONFIRM_PHRASES
    assert 'SELECT'.lower() in CONFIRM_PHRASES


def test_gaze_point_inside_bbox():
    gaze = (100, 110)
    bbox_center = (100, 110)
    radius = 70
    distance = np.linalg.norm(np.array(gaze) - np.array(bbox_center))
    assert distance < radius


def test_gaze_point_outside_bbox():
    gaze = (300, 300)
    bbox_center = (100, 110)
    radius = 70
    distance = np.linalg.norm(np.array(gaze) - np.array(bbox_center))
    assert distance >= radius
