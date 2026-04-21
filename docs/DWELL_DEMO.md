# Dwell VLA Demo

Eye-gaze controlled VLA trigger for the UR12e. Stare at a detected object for the dwell period and `lerobot-record` fires automatically with the gaze coordinates injected.

---

## Hardware

| Device | Role |
|---|---|
| `/dev/video0` | Eye-tracking camera (EyeGestures v2) |
| `/dev/video2` | Scene camera — Brio 100 (workspace view) |
| `/dev/video4` | Side camera (used by lerobot internally) |

---

## One-time setup

```bash
cd ~/EECE5552_Course_Project
source install/setup.bash
```

If you changed any code since the last build:

```bash
colcon build --packages-select perception user_interface
source install/setup.bash
```

---

## Run

```bash
ros2 launch launch/dwell_vla.launch.py \
  scene_device:=/dev/video2 \
  eye_cam_index:=0
```

That starts three nodes:

| Node | What it does |
|---|---|
| `v4l2_camera_node` | Opens `/dev/video2`, publishes to `/cameras/front/image_raw` |
| `vla_detector_multi` | HSV detection for red/blue/yellow, publishes `/vla/coords` + `/vla/detections` + `/vla/preview` |
| `dwell_vla_node` | EyeGestures v2 calibration + fullscreen pygame UI + fires lerobot on dwell |

**Simpler `/vla/coords` only (no dwell UI):** [`scripts/ur12e/pub_coords.sh`](../scripts/ur12e/pub_coords.sh) runs **`vla_detector`** on **`/cameras/front/image_raw`** for LeRobot gaze scripts—see [README — Repo map](../README.md#repo-map) and [UR12E_IL_PIPELINE — Key nodes…](UR12E_IL_PIPELINE.md#key-nodes-launches-and-helper-scripts).

---

## Launch arguments

| Arg | Default | Description |
|---|---|---|
| `scene_device` | `/dev/video2` | Scene camera USB device |
| `eye_cam_index` | `0` | Integer index for eye-tracking camera |
| `colors` | `["red","blue","yellow"]` | Colors to detect |
| `dwell_time` | `2.0` | Seconds of gaze hold before trigger |
| `cooldown_time` | `5.0` | Seconds before same object can re-trigger |

Example with overrides:

```bash
ros2 launch launch/dwell_vla.launch.py \
  scene_device:=/dev/video2 \
  eye_cam_index:=0 \
  dwell_time:=1.5 \
  colors:='["red"]'
```

---

## Calibration

On launch the screen goes dark with cyan dots. Look at each dot and hold until it moves to the next one. Completes automatically after 10 points.

- **`R`** — restart calibration at any time
- **`Q` / `ESC`** — quit

---

## After calibration

The scene camera feed goes fullscreen. Each detected object gets:
- Outer ring — object indicator
- Inner circle — the dwell trigger zone (look here)
- Green arc — fills as dwell accumulates
- Percentage — dwell progress

When the arc completes, `lerobot-record` launches with the object's camera-space coordinates passed as `gaze_default_x` / `gaze_default_y`. While it runs, all objects show **VLA RUNNING** and no new dwell is accepted.

---

## Suppress MediaPipe warnings

```bash
export PYTHONWARNINGS="ignore::UserWarning"
ros2 launch launch/dwell_vla.launch.py scene_device:=/dev/video2 eye_cam_index:=0
```

---

## Topic reference

| Topic | Type | Publisher | Purpose |
|---|---|---|---|
| `/cameras/front/image_raw` | `sensor_msgs/Image` | `v4l2_camera_node` | Raw scene camera feed |
| `/vla/coords` | `std_msgs/Float32MultiArray` | `vla_detector_multi` | Best detection center — model input |
| `/vla/target` | `std_msgs/String` | `vla_detector_multi` | Best detection color name |
| `/vla/detections` | `robot_interfaces/DetectedList` | `vla_detector_multi` | All detections — UI input |
| `/vla/preview` | `sensor_msgs/Image` | `vla_detector_multi` | Annotated frame — UI background |
| `/vla/target_coords` | `geometry_msgs/Point` | `dwell_vla_node` | Fired object coords |
| `/vla/target_label` | `std_msgs/String` | `dwell_vla_node` | Fired object color |

---

## Files

| File | Description |
|---|---|
| `launch/dwell_vla.launch.py` | Main launch file |
| `src/user_interface/user_interface/dwell_vla_node.py` | Pygame UI + EyeGestures + lerobot trigger |
| `src/perception/perception/nodes/vla_detector_multi.py` | Multi-color HSV detector |
