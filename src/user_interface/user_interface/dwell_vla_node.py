#!/usr/bin/env python3
# VisionGrip — Dwell VLA | ROS2 Jazzy | EyeGestures v2
# Author: abdul rahman | NEU Robotics
import os, subprocess, time, threading, math
import cv2
import numpy as np
import pygame
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Point
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from robot_interfaces.msg import DetectedList

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

_DEFAULT_SCRIPT = os.path.expanduser(
    '~/GitHub/EECE5552_Course_Project/scripts/ur12e/start-act.sh')

# ─── Init pygame first to get real screen size ────────────────────────────────
os.environ['SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR'] = '0'
pygame.init()
pygame.font.init()
_info    = pygame.display.Info()
SCREEN_W = _info.current_w
SCREEN_H = _info.current_h

# ─── Config ───────────────────────────────────────────────────────────────────
CALIB_POINTS = 10
CAM_W, CAM_H = 320, 180
HIT_RADIUS   = 150           # screen-px radius that counts as "hovering"
OUTER_RADIUS = 200           # visual indicator ring radius
GAZE_ALPHA   = 0.2           # EMA smoothing — lower = smoother

# ─── Colors ───────────────────────────────────────────────────────────────────
CUBE_COLORS = {
    'red':    (220,  50,  50),
    'blue':   ( 80, 120, 255),
    'yellow': (220, 200,   0),
}
GAZ_CLR      = (255,  60,  60)
DWELL_BG_CLR = ( 70,  70,  70)
DWELL_FG_CLR = (  0, 220,  60)
DWELL_OK_CLR = (  0, 255, 180)
COOLDOWN_CLR = ( 80,  80, 220)
RUNNING_CLR  = (  0, 180, 255)
DIM_CLR      = (110, 110, 110)
BLUE         = ( 80,  80, 255)
WHITE        = (255, 255, 255)

ARC_WIDTH   = 5
GAZE_RADIUS = 18

F_LABEL = max(20, SCREEN_H // 40)
F_SUB   = max(13, SCREEN_H // 65)
F_CALIB = max(30, SCREEN_H // 26)


def _arc_pts(cx, cy, r, a0, a1, steps=80):
    return [(int(cx + r * math.cos(a0 + (a1 - a0) * i / steps)),
             int(cy + r * math.sin(a0 + (a1 - a0) * i / steps)))
            for i in range(steps + 1)]


def _progress_arc(surf, cx, cy, r, progress):
    bg = _arc_pts(cx, cy, r, 0, 2 * math.pi, 80)
    if len(bg) >= 2:
        pygame.draw.lines(surf, DWELL_BG_CLR, False, bg, ARC_WIDTH)
    if progress <= 0:
        return
    fg = _arc_pts(cx, cy, r, -math.pi / 2,
                  -math.pi / 2 + min(progress, 1.0) * 2 * math.pi,
                  max(3, int(80 * progress)))
    if len(fg) >= 2:
        pygame.draw.lines(surf,
                          DWELL_OK_CLR if progress >= 1.0 else DWELL_FG_CLR,
                          False, fg, ARC_WIDTH)


# ─── EyeGestures v2 thread ────────────────────────────────────────────────────
class EyeThread(threading.Thread):
    def __init__(self, cam_index=0):
        super().__init__(daemon=True)
        self.cam_index    = cam_index
        self.gaze_x       = float(SCREEN_W // 2)
        self.gaze_y       = float(SCREEN_H // 2)
        self._smooth_x    = float(SCREEN_W // 2)
        self._smooth_y    = float(SCREEN_H // 2)
        self.fixation     = False
        self.cam_surface  = None
        self.calibrating  = True
        self.calib_point  = None
        self.calib_radius = 30
        self.calib_iter   = 0
        self.algorithm    = ''
        self.ready        = False
        self._lock        = threading.Lock()
        self._stop        = threading.Event()

    def recalibrate(self):
        with self._lock:
            self.calib_iter  = 0
            self.calibrating = True

    def stop(self): self._stop.set()

    def run(self):
        from eyeGestures.utils import VideoCapture
        from eyeGestures import EyeGestures_v2
        gestures = EyeGestures_v2()
        cap      = VideoCapture(self.cam_index)

        x = np.arange(0, 1.1, 0.2);  y = np.arange(0, 1.1, 0.2)
        xx, yy  = np.meshgrid(x, y)
        cal_map = np.column_stack([xx.ravel(), yy.ravel()])
        np.random.shuffle(cal_map)
        gestures.uploadCalibrationMap(cal_map, context='vla_ctx')
        gestures.setClassicalImpact(2)
        gestures.setFixation(1.0)
        self.ready  = True
        prev_pt     = (0, 0)
        iterator    = 0

        while not self._stop.is_set():
            ret, frame = cap.read()
            if not ret: time.sleep(0.01); continue
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            with self._lock: calibrating = self.calibrating
            calibrate = calibrating and (iterator < CALIB_POINTS)
            try:
                event, calibration = gestures.step(
                    frame_rgb, calibrate, SCREEN_W, SCREEN_H, context='vla_ctx')
            except Exception: continue
            if event is None: continue

            with self._lock:
                self.gaze_x    = float(event.point[0])
                self.gaze_y    = float(event.point[1])
                self._smooth_x = GAZE_ALPHA * self.gaze_x + (1 - GAZE_ALPHA) * self._smooth_x
                self._smooth_y = GAZE_ALPHA * self.gaze_y + (1 - GAZE_ALPHA) * self._smooth_y
                self.fixation  = bool(event.fixation)
                try:    self.algorithm = gestures.whichAlgorithm(context='vla_ctx')
                except: self.algorithm = ''
                if calibrate and calibration is not None:
                    cx, cy = calibration.point
                    self.calib_point  = (int(cx), int(cy))
                    self.calib_radius = int(calibration.acceptance_radius)
                    if (cx, cy) != prev_pt:
                        iterator += 1;  prev_pt = (cx, cy)
                    self.calib_iter = iterator
                else:
                    self.calib_point = None
                    if iterator >= CALIB_POINTS:
                        self.calibrating = False

            small = cv2.resize(frame_rgb, (CAM_W, CAM_H))
            surf  = pygame.surfarray.make_surface(np.transpose(small, (1, 0, 2)))
            with self._lock: self.cam_surface = surf

    def get_state(self):
        with self._lock:
            return (int(self._smooth_x), int(self._smooth_y), self.fixation,
                    self.cam_surface, self.calibrating,
                    self.calib_point, self.calib_radius,
                    self.calib_iter, self.algorithm)


# ─── ROS node — camera + all detections ──────────────────────────────────────
class DwellVlaNode(Node):
    def __init__(self):
        super().__init__('dwell_vla_node')

        self.declare_parameter('script_path',   _DEFAULT_SCRIPT)
        self.declare_parameter('dwell_time',    2.0)
        self.declare_parameter('cooldown_time', 5.0)
        self.declare_parameter('eye_cam_index', 0)

        self.script     = self.get_parameter('script_path').value
        self.dwell_time = self.get_parameter('dwell_time').value
        self.cooldown   = self.get_parameter('cooldown_time').value
        self.eye_cam    = self.get_parameter('eye_cam_index').value

        self._bridge      = CvBridge()
        self._lock        = threading.Lock()
        self._frame       = None
        self._frame_w     = 640
        self._frame_h     = 480
        self._detections  = []       # list of DetectedItem — all colors
        self._active_proc = None

        self._coords_pub = self.create_publisher(Point,  '/vla/target_coords', 10)
        self._label_pub  = self.create_publisher(String, '/vla/target_label',  10)

        self.create_subscription(Image,        '/vla/preview',    self._frame_cb, 10)
        self.create_subscription(DetectedList, '/vla/detections', self._det_cb,   10)

        self.get_logger().info(
            f'[DwellVLA] script={self.script}  dwell={self.dwell_time}s  '
            f'cooldown={self.cooldown}s  eye_cam={self.eye_cam}')

    def _frame_cb(self, msg):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w  = frame.shape[:2]
        with self._lock:
            self._frame = frame;  self._frame_w = w;  self._frame_h = h

    def _det_cb(self, msg):
        with self._lock:
            self._detections = list(msg.item_list)

    def get_scene(self):
        with self._lock:
            return (self._frame.copy() if self._frame is not None else None,
                    self._frame_w, self._frame_h, list(self._detections))

    def script_running(self):
        return self._active_proc is not None and self._active_proc.poll() is None

    def fire(self, raw_cx, raw_cy, name):
        if self.script_running():
            self.get_logger().warn('[DwellVLA] already running — skipping')
            return
        self.get_logger().info(f'[DwellVLA] FIRE  {name}  x={raw_cx}  y={raw_cy}')
        self._active_proc = subprocess.Popen(
            ['bash', self.script, str(raw_cx), str(raw_cy)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pt = Point();  pt.x = float(raw_cx);  pt.y = float(raw_cy);  pt.z = 0.0
        self._coords_pub.publish(pt)
        lbl = String();  lbl.data = name
        self._label_pub.publish(lbl)

    def destroy_node(self):
        if self.script_running():
            self._active_proc.terminate()
        super().destroy_node()


# ─── Pygame main loop ─────────────────────────────────────────────────────────
def run_pygame(node: DwellVlaNode, eye: EyeThread):
    os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.NOFRAME)
    pygame.display.set_caption('VisionGrip | Dwell VLA')

    f_label = pygame.font.SysFont('monospace', F_LABEL, bold=True)
    f_sub   = pygame.font.SysFont('monospace', F_SUB)
    f_calib = pygame.font.SysFont('monospace', F_CALIB, bold=True)
    clock   = pygame.time.Clock()

    dwell_start  = {}   # {name: monotonic start time} — one per object
    cooldown_end = {}   # {name: monotonic expiry}
    status_msg   = 'Loading eye tracker...'
    running      = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif ev.key == pygame.K_r and eye.ready:
                    eye.recalibrate()
                    dwell_start.clear()
                    status_msg = 'Recalibrating...'

        (gx, gy, fixation, cam_surf, calibrating,
         calib_pt, calib_r, calib_iter, algorithm) = eye.get_state()
        frame, frame_w, frame_h, dets = node.get_scene()
        now = time.monotonic()

        # ── Background ────────────────────────────────────────────────────
        if frame is not None:
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb  = cv2.resize(rgb, (SCREEN_W, SCREEN_H))
            screen.blit(pygame.surfarray.make_surface(rgb.swapaxes(0, 1)), (0, 0))
        else:
            screen.fill((12, 12, 12))

        # ── Loading splash ────────────────────────────────────────────────
        if not eye.ready:
            t = f_calib.render('Loading eye tracker...', True, (150, 150, 150))
            screen.blit(t, (SCREEN_W // 2 - t.get_width() // 2, SCREEN_H // 2))
            pygame.display.flip();  clock.tick(10);  continue

        if status_msg == 'Loading eye tracker...':
            status_msg = 'Calibrating...'

        sx = SCREEN_W / frame_w if frame_w > 0 else 1.0
        sy = SCREEN_H / frame_h if frame_h > 0 else 1.0
        script_live  = node.script_running()
        active_names = {item.name for item in dets if len(item.xywh) >= 2}

        # Drop dwell timers for objects no longer in frame
        for name in list(dwell_start):
            if name not in active_names:
                dwell_start.pop(name)

        # ── Calibration overlay ───────────────────────────────────────────
        if calibrating:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            bar_w = int(SCREEN_W * min(calib_iter, CALIB_POINTS) / CALIB_POINTS)
            pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(0, 0, SCREEN_W, 10))
            pygame.draw.rect(screen, BLUE,         pygame.Rect(0, 0, bar_w,    10))

            t1 = f_calib.render('CALIBRATING', True, (200, 200, 200))
            t2 = f_sub.render(
                f'{min(calib_iter, CALIB_POINTS)} / {CALIB_POINTS}'
                '  —  stare at each dot until it moves', True, DIM_CLR)
            screen.blit(t1, (SCREEN_W // 2 - t1.get_width() // 2, 20))
            screen.blit(t2, (SCREEN_W // 2 - t2.get_width() // 2, 20 + F_CALIB + 8))

            if calib_pt:
                pygame.draw.circle(screen, (30, 30, 140), calib_pt, calib_r + 10)
                pygame.draw.circle(screen, BLUE,          calib_pt, calib_r)
                pygame.draw.circle(screen, WHITE,         calib_pt, 8)
                cnt = f_calib.render(str(min(calib_iter, CALIB_POINTS)), True, (0, 0, 0))
                screen.blit(cnt, (calib_pt[0] - cnt.get_width()  // 2,
                                  calib_pt[1] - cnt.get_height() // 2))

            hint = f_sub.render(
                f'[R] restart  |  auto-completes at {CALIB_POINTS} pts', True, DIM_CLR)
            screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 22))

        else:
            # ── All detected objects simultaneously ───────────────────────
            for item in dets:
                if len(item.xywh) < 2:
                    continue

                ox_s = int(item.xywh[0] * sx)
                oy_s = int(item.xywh[1] * sy)
                color       = CUBE_COLORS.get(item.name, (200, 200, 200))
                dist        = math.hypot(gx - ox_s, gy - oy_s)
                in_cooldown = now < cooldown_end.get(item.name, 0.0)
                hovering    = dist < HIT_RADIUS and not in_cooldown and not script_live

                if in_cooldown:
                    remain = math.ceil(cooldown_end[item.name] - now)
                    pygame.draw.circle(screen, DIM_CLR,     (ox_s, oy_s), OUTER_RADIUS, 2)
                    pygame.draw.circle(screen, COOLDOWN_CLR, (ox_s, oy_s), HIT_RADIUS,  1)
                    cd = f_sub.render(f'cooldown {remain}s', True, COOLDOWN_CLR)
                    screen.blit(cd, (ox_s - cd.get_width() // 2, oy_s + OUTER_RADIUS + 6))

                elif script_live:
                    pygame.draw.circle(screen, RUNNING_CLR, (ox_s, oy_s), OUTER_RADIUS, 2)
                    rs = f_sub.render('VLA RUNNING', True, RUNNING_CLR)
                    screen.blit(rs, (ox_s - rs.get_width() // 2, oy_s + OUTER_RADIUS + 6))

                else:
                    pygame.draw.circle(screen, color, (ox_s, oy_s), OUTER_RADIUS, 2)
                    hit_color = tuple(min(c + 80, 255) for c in color) if hovering else color
                    pygame.draw.circle(screen, hit_color, (ox_s, oy_s), HIT_RADIUS,
                                       3 if hovering else 1)

                    if hovering:
                        if item.name not in dwell_start:
                            dwell_start[item.name] = now
                        else:
                            elapsed  = now - dwell_start[item.name]
                            progress = min(elapsed / node.dwell_time, 1.0)
                            _progress_arc(screen, ox_s, oy_s, OUTER_RADIUS + 12, progress)
                            pct = f_sub.render(f'{int(progress * 100)}%', True, DWELL_FG_CLR)
                            screen.blit(pct, (ox_s - pct.get_width()  // 2,
                                              oy_s - pct.get_height() // 2))
                            if elapsed >= node.dwell_time:
                                node.fire(int(item.xywh[0]), int(item.xywh[1]), item.name)
                                cooldown_end[item.name] = now + node.cooldown
                                dwell_start.pop(item.name, None)
                                status_msg = f'Fired on {item.name}'
                    else:
                        dwell_start.pop(item.name, None)

                lbl = f_label.render(item.name.upper(), True, color)
                screen.blit(lbl, (ox_s - lbl.get_width() // 2,
                                  oy_s - OUTER_RADIUS - F_LABEL - 6))

            if not dets:
                nd = f_sub.render('no objects detected', True, DIM_CLR)
                screen.blit(nd, (SCREEN_W // 2 - nd.get_width() // 2, SCREEN_H // 2))

            if script_live:
                status_msg = 'VLA RUNNING — lerobot-record active'
                bs = f_label.render('VLA RUNNING...', True, RUNNING_CLR)
                screen.blit(bs, (SCREEN_W // 2 - bs.get_width() // 2,
                                 SCREEN_H // 2 + F_LABEL + 8))
            elif dets and not script_live:
                status_msg = 'look at inner circle to select'

            pygame.draw.circle(screen, GAZ_CLR, (gx, gy), GAZE_RADIUS, 2)
            pygame.draw.circle(screen, GAZ_CLR, (gx, gy), 5)
            if fixation:
                pygame.draw.circle(screen, (255, 200, 50), (gx, gy), GAZE_RADIUS + 8, 1)

            alg = f_sub.render(f'algo: {algorithm}', True, DIM_CLR)
            screen.blit(alg, (SCREEN_W - CAM_W - alg.get_width() - 10,
                               SCREEN_H - CAM_H - 42))

        # ── Eye-cam thumbnail ─────────────────────────────────────────────
        if cam_surf:
            cam_s = pygame.transform.scale(cam_surf, (CAM_W, CAM_H))
            cx, cy = SCREEN_W - CAM_W - 10, SCREEN_H - CAM_H - 38
            screen.blit(cam_s, (cx, cy))
            screen.blit(f_sub.render('EYE CAM', True, DIM_CLR), (cx, cy - 18))
            pygame.draw.rect(screen, (70, 70, 70),
                             pygame.Rect(cx - 2, cy - 2, CAM_W + 4, CAM_H + 4), 1)

        # ── Status bar ────────────────────────────────────────────────────
        pygame.draw.line(screen, (40, 40, 40),
                         (0, SCREEN_H - 30), (SCREEN_W, SCREEN_H - 30), 1)
        screen.blit(f_sub.render(status_msg, True, (180, 180, 180)), (10, SCREEN_H - 22))
        rc = f_sub.render('[R] recalibrate  |  [Q / ESC] quit', True, DIM_CLR)
        screen.blit(rc, (SCREEN_W - rc.get_width() - 10, SCREEN_H - 22))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


def main():
    rclpy.init()
    node = DwellVlaNode()

    eye = EyeThread(node.eye_cam)
    eye.start()

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()

    try:
        run_pygame(node, eye)
    finally:
        eye.stop()
        try:
            node.destroy_node()
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
