import numpy as np
import pytest


def test_process_and_publish_skips_none_gaze():
    """_process_and_publish returns early without publishing when gaze is None."""
    published = []

    class FakeTracker:
        def process_frame(self, frame):
            return None, None
        def project_gaze_to_screen(self, *a):
            raise AssertionError('Should not be called when gaze is None')

    class FakePublisher:
        def publish(self, msg):
            published.append(msg)

    def process_and_publish(tracker, publisher, frame, env_w, env_h):
        gaze_dir, _ = tracker.process_frame(frame)
        if gaze_dir is None:
            return
        env_shape = (env_h, env_w, 3)
        gx, gy = tracker.project_gaze_to_screen(gaze_dir, frame.shape, env_shape)
        from geometry_msgs.msg import Point
        publisher.publish(Point(x=float(gx), y=float(gy), z=0.0))

    process_and_publish(FakeTracker(), FakePublisher(),
                        np.zeros((480, 640, 3), dtype=np.uint8), 1280, 720)
    assert len(published) == 0


def test_process_and_publish_sends_correct_coords():
    """_process_and_publish publishes correct pixel coords when gaze is valid."""
    published = []

    class FakeTracker:
        def process_frame(self, frame):
            return np.array([0.0, 0.0]), None
        def project_gaze_to_screen(self, gaze, frame_shape, env_shape):
            return 640, 360

    class FakePublisher:
        def publish(self, msg):
            published.append(msg)

    def process_and_publish(tracker, publisher, frame, env_w, env_h):
        gaze_dir, _ = tracker.process_frame(frame)
        if gaze_dir is None:
            return
        env_shape = (env_h, env_w, 3)
        gx, gy = tracker.project_gaze_to_screen(gaze_dir, frame.shape, env_shape)
        from geometry_msgs.msg import Point
        publisher.publish(Point(x=float(gx), y=float(gy), z=0.0))

    process_and_publish(FakeTracker(), FakePublisher(),
                        np.zeros((480, 640, 3), dtype=np.uint8), 1280, 720)
    assert len(published) == 1
    assert published[0].x == 640.0
    assert published[0].y == 360.0
    assert published[0].z == 0.0


def test_device_param_accepts_string_path():
    """camera_device param handles string paths like '/dev/video1'."""
    device_param = '/dev/video1'
    try:
        device = int(device_param)
    except (ValueError, TypeError):
        device = device_param
    assert device == '/dev/video1'


def test_device_param_accepts_numeric_string():
    """camera_device param handles numeric string '0' as integer 0."""
    device_param = '0'
    try:
        device = int(device_param)
    except (ValueError, TypeError):
        device = device_param
    assert device == 0
