# UR12e with LeRobot

Record imitation learning datasets from the UR12e in Gazebo using LeRobot and the `ros_twist` teleoperator (joystick → MoveIt Servo).

---

## Overview

Data flow:

```
Joystick → joy_node → teleop_twist_joy → /game_controller (Twist)
                                              ↓
lerobot-teleoperate ← ros_twist teleop        ↓
        ↓                                    ↓
ur12e_ros robot → MoveIt Servo → /servo_node/delta_twist_cmds → UR12e
```

- **ros_twist**: Subscribes to `/game_controller`, forwards Twist as 6-DOF actions to LeRobot (in `lerobot_teleoperator_devices`)
- **ur12e_ros**: Robot config for UR12e with MoveIt Servo (in `lerobot_robot_ros`)
- **home_button_node**: B button → return arm to home pose (runs alongside; does not feed into LeRobot)

---

## Prerequisites

1. **Simulation** — UR12e in Gazebo via `sim.launch.py`
2. **Joystick** — USB gamepad (e.g. Xbox)
3. **LeRobot + lerobot-ros** — See setup below

---

## Setup

### 1. ROS packages

```bash
sudo apt install ros-jazzy-joy ros-jazzy-teleop-twist-joy
```

### 2. LeRobot and lerobot-ros

Use the **lerobot-ros included in this project** (`lerobot-ros/`):

```bash
conda create -y -n lerobot-ros python=3.12
conda activate lerobot-ros
conda install -c conda-forge libstdcxx-ng -y

source /opt/ros/jazzy/setup.bash

cd ~/EECE5552_Course_Project/lerobot-ros
pip install -e lerobot_robot_ros lerobot_teleoperator_devices
```

### 3. Build robot_control (includes home_button_node)

```bash
cd ~/EECE5552_Course_Project
colcon build --packages-select robot_control
source install/setup.bash
```

---

## Run

### Terminal 1 — Simulation

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/sim.launch.py
```

Wait for full startup (~30 s).

### Terminal 2 — Joy + teleop_twist_joy + home button

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/teleop_joy_for_lerobot.launch.py
```

Starts:

- joy_node
- teleop_twist_joy (publishes Twist to `/game_controller`)
- home_button_node (B → home pose)

### Terminal 3 — LeRobot teleoperate

```bash
conda activate lerobot-ros
source /opt/ros/jazzy/setup.bash

lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist
```

---

## Joystick Mapping

| Input        | Effect              |
|-------------|---------------------|
| RB (hold)   | Enable twist input  |
| Left stick X| Left / right        |
| Left stick Y| Forward / back      |
| Right stick Y | Up / down        |
| **B button**| **Return to home pose** |

For imitation learning data collection, do not use the B button during demonstrations. It should only be used to reset the setup between episodes, because it triggers a separate ROS home action outside LeRobot's teleoperation action stream.

---

## Recording

Use `lerobot-record` instead of `lerobot-teleoperate` when recording episodes:

```bash
lerobot-record \
  --robot.type=ur12e_ros \
  --teleop.type=ros_twist \
  --dataset.repo_id=frazier-z/ur12e \
  --dataset.root=$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_sim_dataset \
  --dataset.push_to_hub=false \
  --dataset.num_episodes=5 \
  --dataset.episode_time_s=45 \
  --dataset.reset_time_s=20 \
  --dataset.single_task="pick up imaginary block" \
  --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/top/image_raw', width: 640, height: 480, fps: 30 }, side: {type: opencv, index_or_path: 'ros:///cameras/side/image_raw', width: 640, height: 480, fps: 30 }, front: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 30 } }" \
  --resume false
```

The canonical runnable example lives at `scripts/ur12e/record.sh`. Keep that script as the source of truth for this project and update this doc when the script changes.

Configure cameras via `--robot.cameras.*` as needed. See [LeRobot docs](https://huggingface.co/docs/lerobot) for dataset format and training.

**Note:** B-button home is *not* recorded as an action. It triggers a separate trajectory; LeRobot records zero (or last) velocities during the home move. Trim or exclude those segments if they affect training.

**Camera mode recommendation:** For this project, prefer ROS-topic camera URIs (`ros:///...`) with `ur12e_ros`. The legacy OpenCV `/dev/video*` path and v4l2/ffmpeg bridge path were unstable and could hang or drop frames.

---

## lerobot-ros Integration for UR12e

This project uses the local `lerobot-ros` plugin packages (`lerobot_robot_ros` and `lerobot_teleoperator_devices`) rather than only stock LeRobot behavior.

### Why this was needed

- The `lerobot-ros` code used in this repo targets an older LeRobot integration model.
- Newer LeRobot versions include native ROS-topic camera support, but this project's plugin stack did not expose that behavior out of the box.
- To keep `ur12e_ros` working in this repo without migrating the full stack, we added ROS-topic camera support directly in the local plugin.

### How UR12e is configured

- `lerobot-ros/lerobot_robot_ros/lerobot_robot_ros/config.py`
  - Registers `ur12e_ros` via `@RobotConfig.register_subclass("ur12e_ros")`
  - Defines UR12e-specific joint names, base link (`tool0`), and velocity limits
- `lerobot-ros/lerobot_robot_ros/lerobot_robot_ros/robot.py`
  - `UR12eROS` inherits from `ROS2Robot`
  - `ROS2Robot` handles robot IO and camera construction
- `lerobot-ros/lerobot_teleoperator_devices/.../config_ros_twist.py`
  - Registers `ros_twist` teleoperator for joystick Twist input

When you run `--robot.type=ur12e_ros --teleop.type=ros_twist`, LeRobot instantiates these plugin classes from `lerobot-ros`.

### How ROS-topic camera input was added

Two core changes were made in `lerobot_robot_ros`:

1. Added `lerobot-ros/lerobot_robot_ros/lerobot_robot_ros/ros_topic_camera.py`
   - Implements `ROSTopicCamera`
   - Subscribes to `sensor_msgs/Image` topic
   - Converts incoming image data to BGR `np.ndarray`
   - Stores latest frame thread-safely
   - Exposes `connect()`, `async_read(timeout_ms=...)`, and `disconnect()` so it behaves like a LeRobot camera source

2. Updated `lerobot-ros/lerobot_robot_ros/lerobot_robot_ros/robot.py`
   - Added `ROS2Robot._make_cameras()` to intercept camera configs
   - If `index_or_path` is a ROS URI (`ros:///...` or normalized `ros:/...`), create `ROSTopicCamera`
   - Otherwise fall back to standard LeRobot camera creation (`make_cameras_from_configs`)

### How this integrates at runtime

1. `lerobot-record` parses `--robot.cameras`
2. For `ur12e_ros`, `ROS2Robot._make_cameras()` runs
3. ROS URI cameras are routed to `ROSTopicCamera`
4. Record loop calls `cam.async_read(...)` and receives frames from ROS topics directly

This bypasses `/dev/video*`, v4l2loopback, and ffmpeg for ROS-topic cameras.

### Camera URI format notes

- Recommended in config: `ros:///cameras/top/image_raw`
- Parser may normalize and display: `ros:/cameras/top/image_raw`
- Custom parser logic in `ros_topic_camera.py` accepts both forms, plus path-like values (`PosixPath`)

---

## Files

| File / launch              | Role                                          |
|---------------------------|-----------------------------------------------|
| `teleop_joy_for_lerobot.launch.py` | joy + teleop_twist_joy + home_button_node |
| `lerobot-ros/lerobot_teleoperator_devices/.../ros_twist.py` | Twist → 6-DOF (in this project) |
| `lerobot-ros/lerobot_robot_ros/.../config.py` | ur12e_ros config (tool0, velocity limits) |
| `robot_control/home_button_node.py`           | B → home pose                     |

---

## Troubleshooting

**`ur12e_ros` or `ros_twist` not found**

- Ensure lerobot-ros is installed: `pip install -e lerobot_robot_ros lerobot_teleoperator_devices`
- Uninstall any old `lerobot_teleoperator_ros_twist` or `lerobot_robot_ur12e` packages

**Robot doesn’t move**

- Hold RB
- Confirm `/game_controller` is publishing: `ros2 topic echo /game_controller`

**Wrong axis directions**

- ros_twist maps teleop_twist_joy linear.x/y for tool0 frame; mapping is fixed in code

**Cameras hang or timeout**

- Avoid `lerobot-find-cameras opencv` for this setup; it may hang during device probing.
- Prefer ROS-topic cameras in `--robot.cameras` (example in `scripts/ur12e/record.sh`).
- If logs show `ros:/...` instead of `ros:///...`, that parser normalization is expected.
- If using the old v4l2 route, expect higher CPU/latency and possible frame timeouts.

---

## Related

- [UR12E_TELEOP.md](UR12E_TELEOP.md) — Standalone joystick teleop (no LeRobot)
- [SO101_IMITATION_LEARNING.md](SO101_IMITATION_LEARNING.md) — SO101 POC and LeRobot workflow
- [simulation/README.md](../simulation/README.md) — Sim setup
