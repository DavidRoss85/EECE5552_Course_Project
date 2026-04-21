# Eye-Gaze Controlled Robotic Arm — VisionGrip

**EECE 5552 Assistive Robotics | Northeastern University Seattle**

Control a UR12e robotic arm using only your eyes. Look at a colored cube on the table — the system detects it, highlights it with a bounding box, and publishes its coordinates for downstream control.

---

## System Overview

```
Webcam → EyeGestures v2 → /gaze_tracking/gaze_coords (px)
                                        ↓
Sim Camera → OpenCV HSV detection → /perception/detections (bboxes)
                                        ↓
              gaze_overlay_node → /vla/target_coords (hovered cube center px)
                               → /vla/target_label  (color name)
                                        ↓
            [optional] object_localizer → /goal_pose (3D world pose)
                                        ↓
                              MoveIt2 → UR12e arm moves
```

**Selection model:** Gaze-to-aim. The overlay continuously publishes the pixel coords of whatever cube the gaze is over. No dwell timer — voice-based confirmation will be added later via the `intent_selection` package.

---

## Package Layout

| Package | Node | Responsibility |
|---------|------|----------------|
| `gaze_tracking` | `gaze_tracking_node` | EyeGestures v2 tracker, publishes gaze pixel |
| `perception` | `detection_node` | OpenCV HSV color detection, publishes bboxes + camera image |
| `perception` | `object_localizer_node` | Optional depth backprojection → 3D goal pose |
| `user_interface` | `gaze_overlay_node` | Pygame overlay, publishes VLA target coords |
| `robot_control` | `goal_controller` | MoveIt2 arm controller (depth mode only) |
| `intent_selection` | *(stub)* | Voice recognition — not yet implemented |

---

## Prerequisites

### System
- Ubuntu 24.04
- ROS2 Jazzy
- Gazebo Harmonic
- MoveIt2 (binary install)

### ROS2 Packages
```bash
sudo apt install ros-jazzy-ur ros-jazzy-ur-simulation-gz ros-jazzy-ur-moveit-config \
     ros-jazzy-moveit ros-jazzy-ros-gz-bridge ros-jazzy-topic-tools ros-jazzy-tf2-ros
```

### Python Dependencies
```bash
pip3 install pygame opencv-python scikit-learn --break-system-packages
```

EyeGestures must be installed from source:
```bash
git clone https://github.com/NativeSensors/EyeGestures.git ~/EyeGestures
cd ~/EyeGestures && pip3 install . --break-system-packages
```

> **Note:** YOLO / ultralytics is no longer required. Detection is pure OpenCV.

---

## Build

```bash
cd ~/EECE5552_Course_Project
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

---

## Running the System

### Terminal 1 — Simulation

```bash
ros2 launch launch/sim.launch.py
```

Wait ~15 seconds. This brings up:
- Gazebo with UR12e on a table + 3 colored cubes (red, blue, yellow)
- MoveIt2 move_group
- Camera bridge (top/side/front → ROS2 topics)
- Table registered as MoveIt collision object

### Terminal 2 — Eye-Gaze Pipeline

With webcam (real mode):
```bash
ros2 launch launch/eyegaze.launch.py camera_source:=topic
```

Without webcam (dev/demo mode — sinusoidal dummy gaze):
```bash
ros2 launch launch/eyegaze.launch.py test_mode:=true camera_source:=topic
```

A 1920×1080 borderless overlay window opens showing the top-down camera feed.

### With Arm Motion (depth enabled)

Only use this after `sim.launch.py` is fully up — `goal_controller` blocks on MoveIt:
```bash
ros2 launch launch/eyegaze.launch.py camera_source:=topic use_depth:=true
```

### Real Hardware (USB camera)

```bash
ros2 launch launch/eyegaze.launch.py camera_source:=usb camera_device:=/dev/video0
```

### Standalone VLA Detector (test/debug — no full stack needed)

Runs HSV detection and publishes to `/vla/coords`, `/vla/target`, and `/vla/preview` (annotated image topic, always on). Replace `/dev/video4` with your camera device.

**LeRobot / bench shortcut:** [`scripts/ur12e/pub_coords.sh`](../scripts/ur12e/pub_coords.sh) runs the same **`vla_detector`** node against the **ROS** topic **`/cameras/front/image_raw`** (see script header). Use it when `record_gaze.sh` or `start-act.sh` need live **`/vla/coords`**; pass **`red`**, **`blue`**, or **`yellow`** as the first argument to target that cube color. Onboarding table: [README — Repo map](../README.md#repo-map), [UR12E_IL_PIPELINE — Key nodes…](UR12E_IL_PIPELINE.md#key-nodes-launches-and-helper-scripts).

```bash
# headless (default) — detects in background, preview available on /vla/preview
ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video4

# with live OpenCV window
ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video4 -p display:=true
```

View the annotated feed without a window:
```bash
ros2 run rqt_image_view rqt_image_view /vla/preview
```

Filter by color using the `colors` parameter (default: all three):

```bash
# single color
ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video4 -p colors:='["red"]'

# two colors
ros2 run perception vla_detector --ros-args -p camera_source:=usb -p camera_device:=/dev/video4 -p colors:='["red","blue"]'
```

---

## Calibration (real eye-tracking mode)

A yellow circle appears on screen. Stare at it until it moves. Repeat for 25 points. The system enters tracking mode automatically — the circle disappears and the gaze dot (cyan) becomes visible.

---

## Detection — OpenCV HSV Color Detection

The `detection_node` uses HSV thresholding to detect the 3 colored cubes. No neural network, no GPU required.

### HSV Ranges

| Color | H range | S range | V range |
|-------|---------|---------|---------|
| Red | 0–10 + 170–180 | 100–255 | 100–255 |
| Blue | 100–130 | 100–255 | 100–255 |
| Yellow | 20–35 | 100–255 | 100–255 |

Red requires two ranges because hue wraps around 180° in OpenCV.

### Tuning for Real Hardware

If running with a real camera (not Gazebo), the HSV ranges may need adjustment depending on lighting. You can inspect the HSV values of a target color with:

```python
import cv2
import numpy as np

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # click a pixel and print its HSV value
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    print(hsv[cy, cx])  # center pixel HSV
    cv2.imshow('frame', frame)
    if cv2.waitKey(1) == ord('q'):
        break
```

Override ranges at launch via ROS2 parameters if needed (params declared in `detection_node.py`).

### Camera Source

| Mode | Launch arg | Behavior |
|------|-----------|---------|
| ROS topic (sim) | `camera_source:=topic` | Subscribes to a ROS image topic |
| USB camera | `camera_source:=usb` | Opens device directly via OpenCV |

The `detection_node` always republishes the raw camera image on `/perception/camera_image` so the overlay node doesn't need its own camera handle.

---

## Launch Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `test_mode` | `false` | Dummy sinusoidal gaze, no webcam |
| `camera_source` | `topic` | `"topic"` or `"usb"` |
| `camera_topic` | `/input/camera_feed/rgb/full_view` | ROS topic when `camera_source=topic` |
| `camera_device` | `/dev/video0` | USB device when `camera_source=usb` |
| `use_depth` | `false` | Enable depth backprojection and arm motion |

---

## Topic Reference

| Topic | Type | Publisher | Description |
|-------|------|-----------|-------------|
| `/gaze_tracking/gaze_coords` | `geometry_msgs/Point` | `gaze_tracking_node` | Gaze pixel (u, v) at 30 Hz |
| `/gaze_tracking/calibration_point` | `geometry_msgs/Point` | `gaze_tracking_node` | Calibration dot (z≥0=calibrating, z=-1=done) |
| `/perception/camera_image` | `sensor_msgs/Image` | `detection_node` | Raw camera feed republished |
| `/perception/detections` | `robot_interfaces/DetectedList` | `detection_node` | Detected cube bboxes (`item_list[]`) |
| `/vla/target_coords` | `geometry_msgs/Point` | `gaze_overlay_node` | Hovered cube center pixel (u, v) |
| `/vla/target_label` | `std_msgs/String` | `gaze_overlay_node` | Hovered cube color name |
| `/goal_pose` | `geometry_msgs/PoseStamped` | `object_localizer_node` | 3D arm goal (depth mode only) |

---

## Simulation Scene

| Object | Position | Notes |
|--------|----------|-------|
| Red cube | (0.4, 0.2, 0.810) | 0.07×0.07×0.07 m |
| Blue cube | (0.4, 0.0, 0.810) | 0.07×0.07×0.07 m |
| Yellow cube | (0.4, -0.2, 0.810) | 0.07×0.07×0.07 m |
| Top camera | (0.3, 0, 2.2) | Downward-facing, 60° FOV, 1280×720 |

---

## Overlay Window

- **1920×1080** borderless window
- Camera feed scaled to fill the window (bboxes scaled to match)
- Colored bounding boxes per detected cube (red/blue/yellow)
- Cyan gaze dot shows where you're looking
- Highlighted bbox (thicker border + label) when gaze is over a cube
- Yellow circle during calibration phase
- Press **Q** or **ESC** to quit

---

## In Progress / TODO

- **Voice confirmation** (`intent_selection` package) — speak to select the currently gazed-at cube
- **End-effector orientation** — align gripper to face the object before approach

---

## Authors

Mohammed Abdul Rahman — mohammedabdulr.1@northeastern.edu
Northeastern University Seattle | MS Robotics
