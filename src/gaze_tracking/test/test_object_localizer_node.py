import numpy as np
import pytest


def deproject_pixel(u, v, depth, fx, fy, cx, cy):
    X = (u - cx) * depth / fx
    Y = (v - cy) * depth / fy
    Z = depth
    return X, Y, Z


def test_deproject_at_optical_center():
    X, Y, Z = deproject_pixel(320, 240, 1.0, fx=600, fy=600, cx=320, cy=240)
    assert abs(X) < 1e-9
    assert abs(Y) < 1e-9
    assert abs(Z - 1.0) < 1e-9


def test_deproject_offset_pixel():
    X, Y, Z = deproject_pixel(370, 290, 2.0, fx=500, fy=500, cx=320, cy=240)
    assert abs(X - (370 - 320) * 2.0 / 500) < 1e-9
    assert abs(Y - (290 - 240) * 2.0 / 500) < 1e-9
    assert abs(Z - 2.0) < 1e-9


def test_deproject_zero_depth_returns_zeros():
    X, Y, Z = deproject_pixel(100, 100, 0.0, fx=600, fy=600, cx=320, cy=240)
    assert X == 0.0
    assert Y == 0.0
    assert Z == 0.0


def test_camera_info_intrinsics_extraction():
    K = [600.0, 0.0, 320.0, 0.0, 600.0, 240.0, 0.0, 0.0, 1.0]
    fx, fy, cx, cy = K[0], K[4], K[2], K[5]
    assert fx == 600.0
    assert fy == 600.0
    assert cx == 320.0
    assert cy == 240.0
