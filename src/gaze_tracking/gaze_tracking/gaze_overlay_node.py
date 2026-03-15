import os
import threading
import numpy as np
import cv2
import pygame
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Point
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

from robot_interfaces.msg import DetectedList
from gaze_tracking.gaze_utils import DwellSelectionSystem

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

CONFIRM_PHRASES = {'select', 'grab', 'yes', 'confirm', 'take'}

CAM_W, CAM_H = 1280, 720  # env camera native resolution


class GazeOverlayNode(Node):
    def __init__(self):
        super().__init__('gaze_overlay_node')

        self.declare_parameter('dwell_threshold', 1.5)
        self.declare_parameter('rgb_topic', '/input/camera_feed/rgb/full_view')

        dwell_thresh = self.get_parameter('dwell_threshold').value
        rgb_topic = self.get_parameter('rgb_topic').value

        self._bridge = CvBridge()
        self._dwell = DwellSelectionSystem(dwell_threshold=dwell_thresh)
        self._lock = threading.Lock()
        self._current_detections = []
        self._gaze_point = None
        self._latest_frame = None
        self._calibrating = True
        self._calib_cx = CAM_W // 2
        self._calib_cy = CAM_H // 2
        self._calib_radius = 30

        self._selected_pub = self.create_publisher(Point, '/gaze_tracking/selected_point', 10)

        self.create_subscription(Image, rgb_topic, self._image_cb, 10)
        self.create_subscription(
            DetectedList, '/intent_selection/detections', self._detections_cb, 10)
        self.create_subscription(
            Point, '/input/eye_gaze/coords', self._gaze_cb, 10)
        self.create_subscription(
            String, '/intent_selection/text_commands', self._voice_cb, 10)
        self.create_subscription(
            Point, '/gaze_tracking/calibration_point', self._calib_cb, 10)

        self.get_logger().info('Gaze overlay node ready')

    # ── ROS callbacks ──────────────────────────────────────────────────────────

    def _image_cb(self, msg):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        with self._lock:
            self._latest_frame = frame

    def _detections_cb(self, msg):
        with self._lock:
            self._current_detections = msg.item_list

            # Build new target list from detections
            new_targets = []
            for item in self._current_detections:
                if len(item.xyxy) < 4:
                    continue
                x1, y1, x2, y2 = item.xyxy[0], item.xyxy[1], item.xyxy[2], item.xyxy[3]
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                radius = max(int(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 2), 20)
                new_targets.append((item.name, center, radius))

            # Merge: update position of existing targets to avoid resetting dwell state
            existing = {t.name: t for t in self._dwell.targets}
            updated = []
            for name, center, radius in new_targets:
                if name in existing:
                    t = existing[name]
                    t.center = center
                    t.radius = radius
                    updated.append(t)
                else:
                    from gaze_tracking.gaze_utils import DwellTarget
                    updated.append(DwellTarget(
                        center=center, radius=radius,
                        dwell_time=0.0, dwell_threshold=self._dwell.dwell_threshold,
                        selected=False, name=name,
                    ))
            self._dwell.targets = updated

    def _gaze_cb(self, msg):
        with self._lock:
            self._gaze_point = (int(msg.x), int(msg.y))

    def _calib_cb(self, msg):
        with self._lock:
            self._calibrating = msg.z >= 0.0
            self._calib_cx = int(msg.x)
            self._calib_cy = int(msg.y)
            self._calib_radius = int(msg.z) if msg.z >= 0 else 30

    def _voice_cb(self, msg):
        if msg.data.strip().lower() not in CONFIRM_PHRASES:
            return
        cx, cy = None, None
        with self._lock:
            if self._dwell.current_target is not None:
                cx, cy = self._dwell.current_target.center
                self._dwell.current_target.selected = True
        if cx is not None:
            self.publish_selected(cx, cy)

    # ── Pygame-safe accessors ──────────────────────────────────────────────────

    def publish_selected(self, cx, cy):
        self._selected_pub.publish(Point(x=float(cx), y=float(cy), z=0.0))
        self.get_logger().info(f'Selected object at pixel ({cx}, {cy})')

    def get_render_state(self):
        with self._lock:
            frame = self._latest_frame.copy() if self._latest_frame is not None else None
            return (
                frame,
                list(self._current_detections),
                self._gaze_point,
                self._calibrating,
                self._calib_cx, self._calib_cy, self._calib_radius,
            )

    def update_dwell(self, gaze_pt):
        with self._lock:
            return self._dwell.update(gaze_pt)

    def draw_dwell_targets(self, canvas):
        with self._lock:
            self._dwell.draw_targets(canvas)

    def reset_dwell(self):
        with self._lock:
            self._dwell.targets = []


def run_pygame(node: GazeOverlayNode):
    os.environ['SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR'] = '0'
    pygame.init()
    pygame.font.init()

    SW, SH = 1920, 1080

    screen = pygame.display.set_mode((SW, SH), pygame.NOFRAME)
    pygame.display.set_caption('VisionGrip - Gaze Selection')

    clock = pygame.time.Clock()
    f_sub = pygame.font.SysFont('monospace', max(14, SH // 60))

    WHITE  = (255, 255, 255)
    DIM    = (110, 110, 110)

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif ev.key == pygame.K_r:
                    node.reset_dwell()
                    node.get_logger().info('Dwell targets reset')

        frame, detections, gaze_pt, calibrating, calib_cx, calib_cy, calib_r = \
            node.get_render_state()

        # -- Build canvas (all cv2 drawing at native cam resolution) --
        if frame is None:
            canvas = np.zeros((CAM_H, CAM_W, 3), dtype=np.uint8)
            cv2.putText(canvas, 'Waiting for camera feed...',
                        (CAM_W // 2 - 240, CAM_H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)
        else:
            canvas = frame.copy()

        if calibrating:
            dim = canvas.copy()
            cv2.rectangle(dim, (0, 0), (CAM_W, CAM_H), (0, 0, 0), -1)
            cv2.addWeighted(dim, 0.5, canvas, 0.5, 0, canvas)
            pt = (calib_cx, calib_cy)
            cv2.circle(canvas, pt, calib_r + 8, (40, 40, 180), -1)
            cv2.circle(canvas, pt, calib_r, (80, 80, 255), -1)
            cv2.circle(canvas, pt, 8, (255, 255, 255), -1)
            cv2.putText(canvas, 'CALIBRATING - stare at the dot',
                        (CAM_W // 2 - 280, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        else:
            for item in detections:
                if len(item.xyxy) < 4:
                    continue
                x1, y1, x2, y2 = item.xyxy[0], item.xyxy[1], item.xyxy[2], item.xyxy[3]
                # bright thick bbox so it's obvious
                cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 200, 255), 3)
                label = f'{item.name} {item.confidence:.2f}'
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.rectangle(canvas, (x1, y1 - lh - 10), (x1 + lw + 4, y1), (0, 200, 255), -1)
                cv2.putText(canvas, label,
                            (x1 + 2, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)

            node.draw_dwell_targets(canvas)

            if gaze_pt is not None:
                cv2.circle(canvas, gaze_pt, 20, (255, 60, 60), 3)
                cv2.circle(canvas, gaze_pt, 5, (255, 60, 60), -1)
                selected = node.update_dwell(gaze_pt)
                if selected:
                    node.publish_selected(*selected.center)

            # detection count badge
            n = len(detections)
            badge = f'{n} obj detected' if n else 'no detections'
            badge_color = (0, 200, 255) if n else (60, 60, 200)
            cv2.putText(canvas, badge, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, badge_color, 2)

        cv2.putText(canvas, 'VisionGrip  |  [r] reset  [q/ESC] quit',
                    (10, CAM_H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (110, 110, 110), 1)

        # -- Convert BGR canvas -> pygame surface -> scale to 1920x1080 --
        canvas_rgb = canvas[:, :, ::-1]
        surf = pygame.surfarray.make_surface(np.transpose(canvas_rgb, (1, 0, 2)))
        surf = pygame.transform.scale(surf, (SW, SH))
        screen.blit(surf, (0, 0))

        # Status bar
        status = 'CALIBRATING' if calibrating else 'TRACKING'
        pygame.draw.line(screen, (40, 40, 40), (0, SH - 28), (SW, SH - 28), 1)
        st = f_sub.render(f'{status}  |  [R] reset  |  [Q / ESC] quit', True, DIM)
        screen.blit(st, (10, SH - 20))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


def main():
    rclpy.init()
    node = GazeOverlayNode()

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        run_pygame(node)
    finally:
        executor.shutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
