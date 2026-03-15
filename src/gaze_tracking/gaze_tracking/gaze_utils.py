import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, List
import time

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))


@dataclass
class GazeRay:
    """3D gaze ray direction"""
    origin: np.ndarray
    direction: np.ndarray
    confidence: float


@dataclass
class DwellTarget:
    """Object that can be selected by dwelling"""
    center: Tuple[int, int]
    radius: int
    dwell_time: float
    dwell_threshold: float
    selected: bool
    name: str


class GazeDirectionTracker:
    def __init__(self):
        """Initialize proper gaze direction tracker"""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Key facial landmarks for head pose
        self.NOSE_TIP = 1
        self.CHIN = 152
        self.LEFT_EYE_CORNER = 263
        self.RIGHT_EYE_CORNER = 33
        self.LEFT_MOUTH = 61
        self.RIGHT_MOUTH = 291

        # Eye landmarks
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]

        # 3D model points for head pose
        self.model_points = np.array([
            (0.0, 0.0, 0.0),          # Nose tip
            (0.0, -330.0, -65.0),     # Chin
            (-225.0, 170.0, -135.0),  # Left eye corner
            (225.0, 170.0, -135.0),   # Right eye corner
            (-150.0, -150.0, -125.0), # Left mouth
            (150.0, -150.0, -125.0)   # Right mouth
        ])

        # Gaze history for smoothing
        self.gaze_history = []
        self.history_size = 5

    def get_head_pose(self, landmarks, frame_shape):
        """Estimate head pose from facial landmarks"""
        h, w = frame_shape[:2]

        # Get 2D landmarks
        image_points = np.array([
            (landmarks[self.NOSE_TIP].x * w, landmarks[self.NOSE_TIP].y * h),
            (landmarks[self.CHIN].x * w, landmarks[self.CHIN].y * h),
            (landmarks[self.LEFT_EYE_CORNER].x * w, landmarks[self.LEFT_EYE_CORNER].y * h),
            (landmarks[self.RIGHT_EYE_CORNER].x * w, landmarks[self.RIGHT_EYE_CORNER].y * h),
            (landmarks[self.LEFT_MOUTH].x * w, landmarks[self.LEFT_MOUTH].y * h),
            (landmarks[self.RIGHT_MOUTH].x * w, landmarks[self.RIGHT_MOUTH].y * h)
        ], dtype=np.float64)

        # Camera matrix
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)

        # Assume no lens distortion
        dist_coeffs = np.zeros((4, 1))

        # Solve PnP
        success, rotation_vec, translation_vec = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        return rotation_vec, translation_vec, camera_matrix, dist_coeffs

    def get_eye_gaze_direction(self, landmarks, frame_shape):
        """Calculate eye gaze direction vector"""
        h, w = frame_shape[:2]

        # Get eye centers
        left_eye_points = []
        for idx in self.LEFT_EYE:
            left_eye_points.append([landmarks[idx].x * w, landmarks[idx].y * h])
        left_eye_center = np.mean(left_eye_points, axis=0)

        right_eye_points = []
        for idx in self.RIGHT_EYE:
            right_eye_points.append([landmarks[idx].x * w, landmarks[idx].y * h])
        right_eye_center = np.mean(right_eye_points, axis=0)

        # Get iris centers
        left_iris_points = []
        for idx in self.LEFT_IRIS:
            left_iris_points.append([landmarks[idx].x * w, landmarks[idx].y * h])
        left_iris_center = np.mean(left_iris_points, axis=0)

        right_iris_points = []
        for idx in self.RIGHT_IRIS:
            right_iris_points.append([landmarks[idx].x * w, landmarks[idx].y * h])
        right_iris_center = np.mean(right_iris_points, axis=0)

        # Calculate gaze vectors for each eye
        left_gaze = left_iris_center - left_eye_center
        right_gaze = right_iris_center - right_eye_center

        # Average the two eyes
        avg_gaze = (left_gaze + right_gaze) / 2

        # Normalize
        norm = np.linalg.norm(avg_gaze)
        if norm > 0:
            avg_gaze = avg_gaze / norm

        return avg_gaze

    def smooth_gaze(self, gaze_vector):
        """Smooth gaze direction"""
        self.gaze_history.append(gaze_vector)
        if len(self.gaze_history) > self.history_size:
            self.gaze_history.pop(0)
        return np.mean(self.gaze_history, axis=0)

    def project_gaze_to_screen(self, gaze_2d, frame_shape, target_shape):
        """Project 2D gaze direction to target screen"""
        h, w = frame_shape[:2]
        target_h, target_w = target_shape[:2]

        # Scale gaze direction to target size
        gaze_x = int((gaze_2d[0] + 1) * 0.5 * target_w)
        gaze_y = int((gaze_2d[1] + 1) * 0.5 * target_h)

        gaze_x = np.clip(gaze_x, 0, target_w - 1)
        gaze_y = np.clip(gaze_y, 0, target_h - 1)

        return gaze_x, gaze_y

    def process_frame(self, frame):
        """Process frame and return gaze direction"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return None, None

        landmarks = results.multi_face_landmarks[0].landmark

        try:
            # Get head pose
            rotation_vec, translation_vec, camera_matrix, dist_coeffs = self.get_head_pose(
                landmarks, frame.shape
            )

            # Get eye gaze direction
            eye_gaze = self.get_eye_gaze_direction(landmarks, frame.shape)

            # Smooth gaze
            smoothed_gaze = self.smooth_gaze(eye_gaze)

            return smoothed_gaze, (rotation_vec, translation_vec, camera_matrix, dist_coeffs)
        except Exception:
            return None, None

    def draw_head_pose(self, frame, landmarks, rotation_vec, translation_vec, camera_matrix, dist_coeffs):
        """Draw head pose axes"""
        h, w = frame.shape[:2]

        # Project 3D points for axes
        nose_tip_2d = np.array([
            landmarks[self.NOSE_TIP].x * w,
            landmarks[self.NOSE_TIP].y * h
        ], dtype=np.float64)

        # Draw axes
        axis_length = 100
        axis = np.float32([
            [axis_length, 0, 0],
            [0, axis_length, 0],
            [0, 0, axis_length]
        ])

        imgpts, _ = cv2.projectPoints(axis, rotation_vec, translation_vec, camera_matrix, dist_coeffs)

        nose_tip = tuple(nose_tip_2d.astype(int))

        # X-axis (red)
        cv2.line(frame, nose_tip, tuple(imgpts[0].ravel().astype(int)), (0, 0, 255), 3)
        # Y-axis (green)
        cv2.line(frame, nose_tip, tuple(imgpts[1].ravel().astype(int)), (0, 255, 0), 3)
        # Z-axis (blue)
        cv2.line(frame, nose_tip, tuple(imgpts[2].ravel().astype(int)), (255, 0, 0), 3)


class DwellSelectionSystem:
    def __init__(self, dwell_threshold=1.5):
        """Initialize dwell-based selection system"""
        self.dwell_threshold = dwell_threshold  # seconds
        self.targets: List[DwellTarget] = []
        self.current_target = None
        self.dwell_start_time = None

    def add_target(self, center, radius, name):
        """Add a selectable target"""
        self.targets.append(DwellTarget(
            center=center,
            radius=radius,
            dwell_time=0.0,
            dwell_threshold=self.dwell_threshold,
            selected=False,
            name=name
        ))

    def update(self, gaze_point):
        """Update dwell timers based on gaze point"""
        current_time = time.time()
        looking_at_target = False

        for target in self.targets:
            if target.selected:
                continue

            # Check if gaze is within target
            distance = np.linalg.norm(np.array(gaze_point) - np.array(target.center))

            if distance < target.radius:
                looking_at_target = True

                if self.current_target != target:
                    # Started looking at new target
                    self.current_target = target
                    self.dwell_start_time = current_time
                else:
                    # Continue looking at same target
                    target.dwell_time = current_time - self.dwell_start_time

                    if target.dwell_time >= target.dwell_threshold:
                        target.selected = True
                        return target
            else:
                # Not looking at this target
                if self.current_target == target:
                    self.current_target = None
                    self.dwell_start_time = None
                target.dwell_time = 0.0

        if not looking_at_target:
            self.current_target = None
            self.dwell_start_time = None

        return None

    def draw_targets(self, frame):
        """Draw all targets with dwell progress"""
        for target in self.targets:
            if target.selected:
                # Draw as selected (filled green)
                cv2.circle(frame, target.center, target.radius, (0, 255, 0), -1)
                cv2.circle(frame, target.center, target.radius, (255, 255, 255), 3)

                cv2.putText(frame, "SELECTED",
                            (target.center[0] - 60, target.center[1] + 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            else:
                # Draw as unselected
                cv2.circle(frame, target.center, target.radius, (100, 100, 100), 3)

                # Draw dwell progress
                if target.dwell_time > 0:
                    progress = target.dwell_time / target.dwell_threshold
                    angle = int(360 * progress)

                    # Draw progress arc
                    axes = (target.radius, target.radius)
                    cv2.ellipse(frame, target.center, axes, -90, 0, angle, (0, 255, 255), 5)

                    # Draw filling circle
                    fill_radius = int(target.radius * progress)
                    if fill_radius > 0:
                        cv2.circle(frame, target.center, fill_radius, (0, 200, 200), -1)

            # Draw label
            cv2.putText(frame, target.name,
                        (target.center[0] - 40, target.center[1] - target.radius - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
