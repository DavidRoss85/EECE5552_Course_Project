# UR12e Simulation Environment

## Overview

This simulation environment sets up a UR12e robotic arm mounted on a work table in Gazebo Harmonic, with MoveIt 2, MoveIt Servo, and three cameras for workspace observation.

**Stack:** ROS 2 Jazzy | Gazebo Harmonic | MoveIt 2 | Ubuntu 24.04

---

## Directory Structure

```
simulation/
├── worlds/
│   └── ur12e_table.world              # Gazebo world: table + 3 cameras
├── assets/
│   ├── ur12e_table_mounted.urdf.xacro # UR12e mounted on table
│   └── ur12e_cameras.rviz             # RViz config
└── README.md                          # this file

launch/
├── sim.launch.py                      # main launch (Gazebo + MoveIt + Servo + automation)
├── teleop.launch.py                   # joystick teleop (joy + teleop_twist_joy + teleop_controller)
└── camera_bridge.launch.py            # gz → ROS 2 camera bridge (included in sim)

src/robot_control/robot_control/
├── environment_setup.py               # publishes table to MoveIt planning scene
├── goal_controller.py                 # accepts /goal_pose and executes motion
└── teleop_controller.py               # bridges twist → Servo, B button → home

scripts/
└── send_goal.py                       # sends a pose goal to the robot
```

---

## Prerequisites

### ROS 2 Jazzy + Gazebo Harmonic

```bash
sudo apt install ros-jazzy-moveit
sudo apt install ros-jazzy-ur-simulation-gz
sudo apt install ros-jazzy-ur-robot-driver
sudo apt install ros-jazzy-ros-gz-bridge
sudo apt install ros-jazzy-joy ros-jazzy-teleop-twist-joy
```

### NVIDIA GPU (if applicable)

If you have an NVIDIA GPU, add these to your `~/.bashrc` to prevent Gazebo from crashing:

```bash
echo 'export __NV_PRIME_RENDER_OFFLOAD=1' >> ~/.bashrc
echo 'export __GLX_VENDOR_LIBRARY_NAME=nvidia' >> ~/.bashrc
echo 'export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json' >> ~/.bashrc
source ~/.bashrc
```

If you do **not** have an NVIDIA GPU, skip this step.

---

## Build

```bash
cd ~/EECE5552_Course_Project
colcon build --packages-select robot_control
source install/setup.bash
```

---

## Launch

### Step 1 — Launch the simulation (Terminal 1)

`sim.launch.py` starts Gazebo, MoveIt, Servo, and runs the full setup automatically:

- **10 s:** MoveGroup, RViz, Servo
- **12 s:** Table published to planning scene (`environment_setup`)
- **15 s:** Camera bridge
- **18 s:** Arm moves to home pose (elbow up)
- **24–25 s:** Controller switch (trajectory → forward_position for Servo)
- **27 s:** Servo set to TWIST mode

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/sim.launch.py
```

Wait for "You can start planning now!" and for the automated steps to complete (~30 seconds total).

---

### Step 2 — Launch teleop (Terminal 2)

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/teleop.launch.py
```

This starts joy_node, teleop_twist_joy, and teleop_controller. See [docs/UR12E_TELEOP.md](../docs/UR12E_TELEOP.md) for joystick mapping and B-button home.

---

### Goal-based control (alternative to teleop)

#### Start the goal controller (Terminal 2)

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 run robot_control goal_controller
```

#### Send a goal (Terminal 3)

```bash
source /opt/ros/jazzy/setup.bash
cd ~/EECE5552_Course_Project
python3 scripts/send_goal.py --x -0.1 --y 0.3 --z 1.3
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--x` | -0.1 | X position in world frame (m) |
| `--y` | 0.3 | Y position in world frame (m) |
| `--z` | 1.3 | Z position in world frame (m) |
| `--qx` … `--qw` | 0,0,0,1 | Orientation quaternion |

---

## Camera Topics

Bridged automatically by `sim.launch.py`:

| Camera | Topic | View |
|--------|-------|------|
| Top | `/cameras/top/image_raw` | Bird's eye |
| Side | `/cameras/side/image_raw` | Full robot side |
| Front | `/cameras/front/image_raw` | Full robot front |

```bash
ros2 run rqt_image_view rqt_image_view
```

---

## Robot Details

| Property | Value |
|----------|-------|
| Robot | Universal Robots UR12e |
| DOF | 6 |
| Base frame | `world` |
| Planning group | `ur_manipulator` |
| End effector | `tool0` |
| Table height | 0.775 m |
| Robot base | x=-0.3, y=0, z=0.775 |

### Joint names

| Joint | Description |
|-------|-------------|
| `shoulder_pan_joint` | Base rotation |
| `shoulder_lift_joint` | Shoulder |
| `elbow_joint` | Elbow bend |
| `wrist_1_joint` | First wrist |
| `wrist_2_joint` | Second wrist |
| `wrist_3_joint` | Tool flange |

---

## Troubleshooting

**Gazebo crashes**
- Set NVIDIA env vars if using an NVIDIA GPU
- Verify `nvidia-smi` works

**Multiple robots / leftover processes**
```bash
pkill -f gz; pkill -f rviz2; pkill -f move_group; sleep 3
```

**Goal rejected / CONTROL_FAILED**
- Ensure sim is fully up (~30 s)
- Check joint states: `ros2 topic echo /joint_states --once`

**warehouse_sqlite_path error**
- Use `sim.launch.py`, not `ur_moveit.launch.py` directly

---

## Related

- [UR12E_TELEOP.md](../docs/UR12E_TELEOP.md) — Joystick teleop and B-button home
- [UR12E_GAZEBO_SETUP.md](../docs/UR12E_GAZEBO_SETUP.md) — UR simulator installation
