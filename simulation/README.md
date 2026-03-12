# UR12e Simulation Environment

## Overview

This simulation environment sets up a UR12e robotic arm mounted on a work table
in Gazebo Harmonic, with MoveIt 2 for motion planning and three cameras for
workspace observation.

**Stack:** ROS2 Jazzy | Gazebo Harmonic | MoveIt 2 | Ubuntu 24.04

---

## Directory Structure
```
simulation/
├── worlds/
│   └── ur12e_table.world        # Gazebo world: table + 3 cameras
├── assets/
│   ├── ur12e_table_mounted.urdf.xacro   # UR12e mounted on table
│   └── ur12e_cameras.rviz               # RViz config
└── README.md                    # this file

launch/
├── sim.launch.py                # main launch file (Gazebo + MoveIt)
└── camera_bridge.launch.py      # gz -> ROS2 camera bridge

src/robot_control/robot_control/
├── environment_setup.py         # publishes table to MoveIt planning scene
└── goal_controller.py           # accepts /goal_pose and executes motion

scripts/
└── send_goal.py                 # sends a pose goal to the robot
```

---

## Prerequisites

### ROS2 Jazzy + Gazebo Harmonic
```bash
sudo apt install ros-jazzy-moveit
sudo apt install ros-jazzy-ur-simulation-gz
sudo apt install ros-jazzy-ur-robot-driver
sudo apt install ros-jazzy-ros-gz-bridge
```

### NVIDIA GPU (if applicable)

If you have an NVIDIA GPU, add these to your `~/.bashrc` to prevent Gazebo
from crashing on the Mesa/EGL fallback:
```bash
echo 'export __NV_PRIME_RENDER_OFFLOAD=1' >> ~/.bashrc
echo 'export __GLX_VENDOR_LIBRARY_NAME=nvidia' >> ~/.bashrc
echo 'export __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json' >> ~/.bashrc
source ~/.bashrc
```

If you do **not** have an NVIDIA GPU, skip this step entirely.

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

This starts Gazebo with the table world, spawns the UR12e on the table,
brings up MoveIt 2, RViz, and the camera bridge.
```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/sim.launch.py
```

Wait for:
```
You can start planning now!
```

Then **hit the play button in Gazebo** to start the simulation.

---

### Step 2 — Set up MoveIt planning scene (Terminal 2)

Publishes the table as a collision object so MoveIt avoids it during planning.
```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 run robot_control environment_setup
```

Expected output:
```
Table published to planning scene
```

---

### Step 3 — Start the goal controller (Terminal 3)

Starts a node that listens for pose goals on `/goal_pose` and sends them
to MoveIt for planning and execution.
```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 run robot_control goal_controller
```

Expected output:
```
MoveGroup ready
Listening on /goal_pose
```

---

### Step 4 — Send a goal (Terminal 4)

Send the robot to a specific XYZ position in the world frame.
```bash
source /opt/ros/jazzy/setup.bash
cd ~/EECE5552_Course_Project
python3 scripts/send_goal.py --x -0.1 --y 0.3 --z 1.3
```

#### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--x`    | -0.1    | X position in world frame (meters) |
| `--y`    | 0.3     | Y position in world frame (meters) |
| `--z`    | 1.3     | Z position in world frame (meters) |
| `--qx`   | 0.0     | Orientation quaternion x |
| `--qy`   | 0.0     | Orientation quaternion y |
| `--qz`   | 0.0     | Orientation quaternion z |
| `--qw`   | 1.0     | Orientation quaternion w |

#### Example goals
```bash
# above table center
python3 scripts/send_goal.py --x -0.1 --y 0.3 --z 1.3

# reach to the side
python3 scripts/send_goal.py --x 0.2 --y 0.4 --z 1.1

# reach forward
python3 scripts/send_goal.py --x 0.4 --y 0.0 --z 1.2
```

---

## Camera Topics

Three cameras are set up in the world. After the sim launches they are
bridged to ROS2 automatically.

| Camera | Topic | View |
|--------|-------|------|
| Top    | `/cameras/top/image_raw`   | Bird's eye view of table |
| Side   | `/cameras/side/image_raw`  | Full robot side view |
| Front  | `/cameras/front/image_raw` | Full robot front view |

### View camera feeds
```bash
# install rqt image view if needed
sudo apt install ros-jazzy-rqt-image-view

# launch image viewer
ros2 run rqt_image_view rqt_image_view
```

Select a topic from the dropdown in the top left.

### Check cameras are publishing
```bash
ros2 topic list | grep cameras
ros2 topic hz /cameras/top/image_raw
```

---

## Robot Details

| Property | Value |
|----------|-------|
| Robot    | Universal Robots UR12e |
| DOF      | 6 |
| Base frame | `world` |
| Planning group | `ur_manipulator` |
| End effector link | `tool0` |
| Table height | 0.775m |
| Robot base position | x=-0.3, y=0, z=0.775 |

### Joint names

| Joint | Description |
|-------|-------------|
| `shoulder_pan_joint`  | Base rotation |
| `shoulder_lift_joint` | Shoulder elevation |
| `elbow_joint`         | Elbow bend |
| `wrist_1_joint`       | First wrist |
| `wrist_2_joint`       | Second wrist |
| `wrist_3_joint`       | Tool flange rotation |

### Check joint states
```bash
ros2 topic echo /joint_states --once
```

---

## Troubleshooting

**Gazebo crashes on launch**
- Make sure NVIDIA env vars are set if you have an NVIDIA GPU
- Check `nvidia-smi` returns valid output

**Multiple robots spawning**
- Previous session wasn't killed cleanly
- Run: `pkill -f gz; pkill -f rviz2; pkill -f move_group; sleep 3`
- Then relaunch

**Goal rejected or CONTROL_FAILED**
- Make sure Gazebo is playing (hit play button)
- Make sure `environment_setup` ran first
- Check joint states are publishing: `ros2 topic echo /joint_states --once`

**warehouse_sqlite_path error**
- Make sure you're using `sim.launch.py` and not launching `ur_moveit.launch.py` directly

---

## Authors

Mohammed Abdul Rahman — mohammedabdulr.1@northeastern.edu
EECE5552 | MS Robotics | Northeastern University
