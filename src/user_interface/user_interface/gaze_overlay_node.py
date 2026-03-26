import threading
import pygame
import cv2
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from robot_interfaces.msg import DetectedList

print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

CUBE_COLORS = {
    'red':    (220,  50,  50),
    'blue':   ( 50,  50, 220),
    'yellow': (220, 220,   0),
}
GAZE_COLOR          = (0, 220, 220)
HIGHLIGHT_THICKNESS = 4
NORMAL_THICKNESS    = 2
GAZE_RADIUS         = 12
LABEL_FONT_SIZE     = 20


class GazeOverlayNode(Node):
    def __init__(self):
        super().__init__('gaze_overlay_node')

        self.declare_parameter('display_width',  1280)
        self.declare_parameter('display_height', 720)

        self._disp_w = self.get_parameter('display_width').value
        self._disp_h = self.get_parameter('display_height').value

        self._bridge = CvBridge()
        self._lock = threading.Lock()

        self._frame       = None
        self._cam_w       = self._disp_w   # updated on first frame
        self._cam_h       = self._disp_h
        self._detections  = []
        self._gaze_x      = self._disp_w // 2
        self._gaze_y      = self._disp_h // 2
        self._calibrating = True
        self._calib_cx    = self._disp_w // 2
        self._calib_cy    = self._disp_h // 2
        self._calib_radius = 30

        self._coords_pub = self.create_publisher(Point,  '/vla/target_coords', 10)
        self._label_pub  = self.create_publisher(String, '/vla/target_label',  10)

        self.create_subscription(Image,       '/perception/camera_image',        self._img_cb,   10)
        self.create_subscription(DetectedList,'/perception/detections',           self._det_cb,   10)
        self.create_subscription(Point,       '/gaze_tracking/gaze_coords',       self._gaze_cb,  10)
        self.create_subscription(Point,       '/gaze_tracking/calibration_point', self._calib_cb, 10)

        self._running = True
        self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
        self._render_thread.start()

        self.get_logger().info(
            f'Gaze overlay node ready ({self._disp_w}x{self._disp_h})')

    def _img_cb(self, msg: Image):
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        with self._lock:
            self._cam_h, self._cam_w = frame.shape[:2]
        frame = cv2.resize(frame, (self._disp_w, self._disp_h))
        with self._lock:
            self._frame = frame

    def _det_cb(self, msg: DetectedList):
        with self._lock:
            self._detections = list(msg.item_list)

    def _gaze_cb(self, msg: Point):
        with self._lock:
            self._gaze_x = int(msg.x)
            self._gaze_y = int(msg.y)

    def _calib_cb(self, msg: Point):
        # z >= 0 → calibrating (z = acceptance radius px)
        # z == -1 → done
        with self._lock:
            if msg.z < 0:
                self._calibrating = False
            else:
                self._calibrating = True
                self._calib_cx     = int(msg.x)
                self._calib_cy     = int(msg.y)
                self._calib_radius = int(msg.z)

    @staticmethod
    def _in_bbox(px, py, xyxy):
        x1, y1, x2, y2 = xyxy
        return x1 <= px <= x2 and y1 <= py <= y2

    def _render_loop(self):
        pygame.init()
        screen = pygame.display.set_mode(
            (self._disp_w, self._disp_h), pygame.NOFRAME)
        pygame.display.set_caption('VisionGrip')
        font  = pygame.font.SysFont('monospace', LABEL_FONT_SIZE, bold=True)
        clock = pygame.time.Clock()

        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        self._running = False

            with self._lock:
                frame  = self._frame.copy() if self._frame is not None else None
                dets   = list(self._detections)
                gx, gy = self._gaze_x, self._gaze_y
                calib  = self._calibrating
                ccx, ccy, cr = self._calib_cx, self._calib_cy, self._calib_radius
                cam_w, cam_h = self._cam_w, self._cam_h

            # Scale factors: bbox coords come in camera resolution, display may differ
            sx = self._disp_w / cam_w if cam_w > 0 else 1.0
            sy = self._disp_h / cam_h if cam_h > 0 else 1.0

            if frame is not None:
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                surface = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
            else:
                surface = pygame.Surface((self._disp_w, self._disp_h))
                surface.fill((20, 20, 20))

            hovered_item  = None
            hovered_color = None

            for item in dets:
                if len(item.xyxy) < 4:
                    continue
                x1 = int(item.xyxy[0] * sx)
                y1 = int(item.xyxy[1] * sy)
                x2 = int(item.xyxy[2] * sx)
                y2 = int(item.xyxy[3] * sy)
                color      = CUBE_COLORS.get(item.name, (200, 200, 200))
                is_hovered = self._in_bbox(gx, gy, (x1, y1, x2, y2))
                thickness  = HIGHLIGHT_THICKNESS if is_hovered else NORMAL_THICKNESS
                pygame.draw.rect(surface, color,
                                 pygame.Rect(x1, y1, x2-x1, y2-y1), thickness)
                if is_hovered:
                    hovered_item  = item
                    hovered_color = item.name
                    label = font.render(item.name.upper(), True, color)
                    surface.blit(label, (x1, max(0, y1 - LABEL_FONT_SIZE - 4)))

            if not calib:
                pygame.draw.circle(surface, GAZE_COLOR, (gx, gy), GAZE_RADIUS, 2)

            if calib:
                pygame.draw.circle(surface, (255, 255, 0), (ccx, ccy), cr, 3)
                pygame.draw.circle(surface, (255, 255, 0), (ccx, ccy), 4)

            screen.blit(surface, (0, 0))
            pygame.display.flip()
            clock.tick(30)

            # Gaze-to-aim: publish continuously while gaze is on a cube.
            # No dwell gate here — voice-based selection will be added in intent_selection pkg.
            if hovered_item is not None and len(hovered_item.xywh) >= 2:
                cx, cy = hovered_item.xywh[0], hovered_item.xywh[1]
                pt = Point()
                pt.x = float(cx)
                pt.y = float(cy)
                pt.z = 0.0
                self._coords_pub.publish(pt)
                lbl = String()
                lbl.data = hovered_color
                self._label_pub.publish(lbl)

        pygame.quit()

    def destroy_node(self):
        self._running = False
        super().destroy_node()


def main():
    rclpy.init()
    node = GazeOverlayNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
