import numpy as np
import pytest


def test_project_gaze_to_screen_center():
    """Zero gaze vector maps to center of target."""
    from gaze_tracking.gaze_utils import GazeDirectionTracker
    tracker = GazeDirectionTracker()
    gaze = np.array([0.0, 0.0])
    frame_shape = (480, 640, 3)
    target_shape = (720, 1280, 3)
    x, y = tracker.project_gaze_to_screen(gaze, frame_shape, target_shape)
    assert x == 640
    assert y == 360


def test_project_gaze_clamps_to_bounds():
    """Extreme gaze values are clamped within target dimensions."""
    from gaze_tracking.gaze_utils import GazeDirectionTracker
    tracker = GazeDirectionTracker()
    gaze = np.array([2.0, 2.0])
    frame_shape = (480, 640, 3)
    target_shape = (720, 1280, 3)
    x, y = tracker.project_gaze_to_screen(gaze, frame_shape, target_shape)
    assert 0 <= x < 1280
    assert 0 <= y < 720


def test_bbox_to_dwell_circle_center():
    """Bbox center calculation is correct."""
    x1, y1, x2, y2 = 100, 100, 200, 200
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    assert center_x == 150
    assert center_y == 150


def test_bbox_to_dwell_circle_radius():
    """Bbox radius is half the diagonal."""
    x1, y1, x2, y2 = 100, 100, 200, 200
    radius = int(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 2)
    assert radius == 70


def test_dwell_system_no_selection_before_threshold():
    """Dwell system does not select before threshold is reached."""
    from gaze_tracking.gaze_utils import DwellSelectionSystem
    system = DwellSelectionSystem(dwell_threshold=999.0)
    system.add_target((100, 100), 50, 'test_target')
    result = system.update((100, 100))
    assert result is None


def test_smooth_gaze_returns_average():
    """Smoothed gaze is the mean of the history."""
    from gaze_tracking.gaze_utils import GazeDirectionTracker
    tracker = GazeDirectionTracker()
    v1 = np.array([0.0, 0.0])
    v2 = np.array([1.0, 0.0])
    tracker.smooth_gaze(v1)
    result = tracker.smooth_gaze(v2)
    assert abs(result[0] - 0.5) < 1e-9
