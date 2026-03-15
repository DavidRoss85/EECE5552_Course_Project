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

```bash
conda create -y -n lerobot-ros python=3.12
conda activate lerobot-ros
conda install -c conda-forge libstdcxx-ng -y

source /opt/ros/jazzy/setup.bash
```

If lerobot-ros is inside this project:

```bash
cd ~/EECE5552_Course_Project/lerobot-ros
pip install -e lerobot_robot_ros lerobot_teleoperator_devices
```

Otherwise clone and install:

```bash
git clone https://github.com/ycheng517/lerobot-ros
cd lerobot-ros
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

With cameras (for recording):

```bash
lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist \
  --robot.cameras.top.fps=30 \
  --robot.cameras.top.index_or_path=0
```

---

## Joystick Mapping

| Input        | Effect              |
|-------------|---------------------|
| RB (hold)   | Enable twist input  |
| Left stick X| Left / right        |
| Left stick Y| Forward / back      |
| Right stick Y | Up / down        |
| Right stick X | Rotate (yaw)      |
| **B button**| **Return to home pose** |

---

## Recording

Use `lerobot-record` instead of `lerobot-teleoperate` when recording episodes:

```bash
lerobot-record \
  --robot.type=ur12e_ros \
  --teleop.type=ros_twist \
  --repo-id=your-username/your-dataset
```

Configure cameras via `--robot.cameras.*` as needed. See [LeRobot docs](https://huggingface.co/docs/lerobot) for dataset format and training.

**Note:** B-button home is *not* recorded as an action. It triggers a separate trajectory; LeRobot records zero (or last) velocities during the home move. Trim or exclude those segments if they affect training.

---

## Files

| File / launch              | Role                                          |
|---------------------------|-----------------------------------------------|
| `teleop_joy_for_lerobot.launch.py` | joy + teleop_twist_joy + home_button_node |
| `lerobot-ros/lerobot_teleoperator_devices/.../ros_twist.py` | Twist → 6-DOF actions          |
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

---

## Related

- [UR12E_TELEOP.md](UR12E_TELEOP.md) — Standalone joystick teleop (no LeRobot)
- [SO101_IMITATION_LEARNING.md](SO101_IMITATION_LEARNING.md) — SO101 POC and LeRobot workflow
- [simulation/README.md](../simulation/README.md) — Sim setup
