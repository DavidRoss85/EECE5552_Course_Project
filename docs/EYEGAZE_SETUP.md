# Eye-Gaze Controlled Robotic Arm

**EECE 5552 Assistive Robotics | Northeastern University Seattle**

Control a UR12e robotic arm using only your eyes. Look at an object on a table — the system detects it, highlights it with a bounding box, and moves the arm to it after a short dwell.

---

## System Overview

```
Webcam → EyeGestures v2 → gaze (px)
                               ↓
Sim Camera → YOLO detection → bboxes + dwell selection → selected pixel
                               ↓
Depth Camera → object_localizer → 3D world pose
                               ↓
                         MoveIt2 → UR12e arm moves
```

**Modes:**
- `test_mode:=true` — sinusoidal dummy gaze, no webcam needed (for development)
- `test_mode:=false` — real EyeGestures v2 eye tracking via webcam

---

## Prerequisites

### System
- Ubuntu 24.04
- ROS2 Jazzy
- Gazebo Harmonic
- MoveIt2 (binary install)
- NVIDIA GPU recommended (YOLO runs on CUDA)

### ROS2 Packages
```bash
sudo apt install ros-jazzy-ur ros-jazzy-ur-simulation-gz ros-jazzy-ur-moveit-config \
     ros-jazzy-moveit ros-jazzy-ros-gz-bridge ros-jazzy-topic-tools \
     ros-jazzy-tf2-ros
```

### Python Dependencies
```bash
pip3 install ultralytics pygame scikit-learn --break-system-packages
```

EyeGestures must be installed from source:
```bash
git clone https://github.com/NativeSensors/EyeGestures.git ~/EyeGestures
cd ~/EyeGestures && pip3 install . --break-system-packages
```

---

## Build

```bash
cd ~/EECE5552_Course_Project
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

---

## Steps to Reproduce

### 1. Launch the Simulation

```bash
ros2 launch launch/sim.launch.py
```

Wait ~15 seconds for all components:
- Gazebo opens with UR12e on a table and a Coke Can
- MoveIt2 move_group starts
- Camera bridge comes up (top/side/front cameras bridged to ROS2)
- Table registered as MoveIt collision object (prevents arm hitting it)

### 2. Launch the Eye-Gaze Pipeline

With webcam:
```bash
ros2 launch launch/eyegaze.launch.py
```

Without webcam (demo/dev mode):
```bash
ros2 launch launch/eyegaze.launch.py test_mode:=true
```

A 1920×1080 overlay window opens showing the top-down camera feed.

### 3. Calibration (real mode only)

A dark overlay appears with a blue dot. Stare at the dot until it moves. Repeat for 25 calibration points. System enters tracking mode automatically.

### 4. Select an Object

- Coke Can highlighted with cyan bounding box when YOLO detects it
- Dwell circle appears around the detected object
- **Look at the bounding box** — hold gaze for ~1.5 seconds
- Circle fills and turns green: "SELECTED"
- Arm moves to 15 cm above the selected object

### 5. Keyboard Controls (overlay window)

| Key | Action |
|-----|--------|
| `R` | Reset dwell targets |
| `Q` / `ESC` | Quit |

---

## Topic Reference

| Topic | Type | Description |
|-------|------|-------------|
| `/input/eye_gaze/coords` | `geometry_msgs/Point` | Gaze pixel coordinates |
| `/gaze_tracking/calibration_point` | `geometry_msgs/Point` | Calibration dot position |
| `/intent_selection/detections` | `robot_interfaces/DetectedList` | YOLO bounding boxes |
| `/gaze_tracking/selected_point` | `geometry_msgs/Point` | Selected pixel after dwell |
| `/goal_pose` | `geometry_msgs/PoseStamped` | 3D arm goal in world frame |
| `/intent_selection/text_commands` | `std_msgs/String` | Voice command input (TODO) |

---

## Cameras

| Camera | Topic | Position | Purpose |
|--------|-------|----------|---------|
| Top | `/cameras/top/image_raw` | `(0.3, 0, 2.2)` overhead | Gaze overlay + detection |
| Side | `/cameras/side/image_raw` | `(4.0, 0, 1.4)` side view | Monitoring |
| Front | `/cameras/front/image_raw` | `(0, -4.0, 1.4)` front view | Monitoring |

---

## In Progress / TODO

- **Voice confirmation** — Speak "select" or "grab" to confirm without full dwell. Stub placeholder in `eyegaze.launch.py`.
- **Robot orientation** — Align end-effector to face the object before approaching.

---

## Authors

Mohammed Abdul Rahman — mohammedabdulr.1@northeastern.edu
Northeastern University Seattle | MS Robotics
