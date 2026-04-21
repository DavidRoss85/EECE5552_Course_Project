# UR12e with LeRobot

Record imitation learning datasets from the UR12e in Gazebo using LeRobot and the `ros_twist` teleoperator (joystick → MoveIt Servo).

**End-to-end ML (record → train → policy), including real robot notes:** see **[UR12E_IL_PIPELINE.md](UR12E_IL_PIPELINE.md)**.

**Onboarding without reading every source file:** Launch docstrings, node module docstrings, and script headers are summarized in the **[README — Repo map](../README.md#repo-map)** and **[UR12E_IL_PIPELINE — Key nodes, launches, and helper scripts](UR12E_IL_PIPELINE.md#key-nodes-launches-and-helper-scripts)** sections.

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

These two packages supply **`joy_node`** and **`teleop_node`** (`teleop_twist_joy`) for the LeRobot joystick launches. They **do not** replace the **UR driver**, **MoveIt**, or **Gazebo** packages—see **[UR12E_IL_PIPELINE — ROS packages to install with apt](UR12E_IL_PIPELINE.md#ros-packages-to-install-with-apt)** for the full **`apt`** list used with this repo.

### 2. LeRobot and lerobot-ros

Use the **lerobot-ros included in this project** (`lerobot-ros/`). Create a **Conda** environment named `lerobot-ros` (keeps LeRobot + CUDA wheels off the system Python used by some ROS tools):

```bash
conda create -y -n lerobot-ros python=3.12
conda activate lerobot-ros
conda install -c conda-forge libstdcxx-ng -y

source /opt/ros/jazzy/setup.bash

cd ~/EECE5552_Course_Project/lerobot-ros   # or your clone path
pip install --upgrade pip
pip install -e lerobot_robot_ros lerobot_teleoperator_devices
```

`pip install -e lerobot_robot_ros` installs **`lerobot`** as a dependency (see `lerobot_robot_ros/pyproject.toml`). After install, `which lerobot-record` should resolve inside the env. For a full **LeRobot CLI** install (PyTorch, `ffmpeg`, troubleshooting), follow **[Hugging Face — LeRobot installation](https://huggingface.co/docs/lerobot/installation)**; the **[README](../README.md#conda-environment-for-lerobot-lerobot-ros)** repeats the env + plugin steps. **Each new shell:** `conda activate lerobot-ros`, then `source /opt/ros/jazzy/setup.bash` and your workspace `install/setup.bash`.

**Tear down / recreate:** `conda env remove -n lerobot-ros -y`, then run the block again.

The repo **[README](../README.md#conda-environment-for-lerobot-lerobot-ros)** duplicates this for newcomers landing on the main page.

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

**Hardware / URSim — main launch:** **`ursim_with_joy_teleop.launch.py`** is the repo’s **primary entry point** for the UR12e driver stack **with** joystick teleop enabled (it includes `ursim.launch.py` plus [`launch/teleop_joy_lerobot_ursim.py`](../launch/teleop_joy_lerobot_ursim.py)). The **`ursim` in nested filenames is a misnomer**—those nodes are not tied to the simulator; they work for **URSim or the live robot** as long as Servo and LeRobot expect `/game_controller`. For driver + MoveIt + Servo **without** bundled joy, launch `ursim.launch.py` alone.

**Per-gamepad tuning:** `teleop_twist_joy` parameters (`enable_button`, `axis_linear.*`, `scale_linear.*`) in `teleop_joy_lerobot_ursim.py` were set for an **older Xbox-style** controller. Other gamepads often need different axis indices or scales. Edit that file (or the Gazebo-oriented [`launch/teleop_joy_for_lerobot.launch.py`](../launch/teleop_joy_for_lerobot.launch.py), which duplicates the same pattern with `use_sim_time`) and **test in Gazebo or URSim** until holding the deadman and moving sticks produces sensible motion—only then use the same mapping on the real arm.

### Terminal 3 — LeRobot teleoperate

```bash
conda activate lerobot-ros
source /opt/ros/jazzy/setup.bash

lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist
```

**Hardware / URSim shortcut:** if you already started **`ursim_with_joy_teleop.launch.py`** (driver + joy in one launch), you only need this terminal for LeRobot. **`ur12e_ros`** and **`ros_twist`** are the **custom** robot and teleop plugins in `lerobot-ros/` described under [Custom plugins and MoveIt Servo control path](#custom-plugins-and-moveit-servo-control-path).

---

## Joystick Mapping

The table matches the **default** `enable_button` / axis indices in the launch files above. If your pad differs, adjust the launch parameters first—do not assume RB/left-stick semantics without checking.

| Input        | Effect              |
|-------------|---------------------|
| RB (hold)   | Enable twist input  |
| Left stick X| Left / right        |
| Left stick Y| Forward / back      |
| Right stick Y | Up / down        |
| **B button**| **Return to home pose** (ROS only; see warning below) |

> **WARNING — B button and the ML pipeline**  
> **B** runs `home_button_node`, which switches controllers and sends a **joint trajectory to home** outside LeRobot. That motion is **not** represented as a coherent teleop action in your dataset (LeRobot may see zeros or stale commands while the arm moves). **Do not press B during a demonstration you intend to train on**; use it only **between** episodes to reset.  
> **WARNING — speed and clearance**  
> The home move uses a **fixed-duration** trajectory (`time_from_start` **6 s** in [`home_button_node.py`](../src/robot_control/robot_control/home_button_node.py)). If the arm starts **far from home in joint space**, the same time budget implies **large joint velocities**—the arm can move **quickly** toward home. **Start near the home pose** and clear the workspace before pressing **B**.

**Home joint targets** (same order as `JOINT_NAMES` in `home_button_node.py`: shoulder pan → wrist 3). Values in the code are radians; approximate **degrees**:

| Joint | Angle (deg) |
|-------|----------------|
| `shoulder_pan_joint` | **179.9** |
| `shoulder_lift_joint` | **−90.0** |
| `elbow_joint` | **90.0** |
| `wrist_1_joint` | **−90.0** |
| `wrist_2_joint` | **−90.0** |
| `wrist_3_joint` | **90.0** |

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

**Note:** B-button home is *not* recorded as a meaningful ML action (see [warnings under Joystick Mapping](#joystick-mapping)). It triggers a separate ROS trajectory; LeRobot records zero (or last) velocities during the home move. Trim or exclude those segments if they affect training.

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

### Custom plugins and MoveIt Servo control path

**Smoke test (teleop only, no dataset):** bring up **`ursim_with_joy_teleop.launch.py`** with the correct **`robot_ip`**, then run **`lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist`** (same as Terminal 3 below). See also the [README smoke-test section](../README.md#smoke-test-teleop-only-lerobot).

- **`ur12e_ros`** — **Custom robot plugin** added in this project’s **`lerobot-ros/lerobot_robot_ros`** (`UR12eROS` registered in `config.py`). It is the LeRobot-side adapter for the UR12e stack: joint state, cameras, gripper topic mode, and—critically—**Cartesian velocity** output to **MoveIt Servo** via **`ROS2Interface.servo()`** → **`MoveIt2Servo.servo()`**, which publishes **`geometry_msgs/TwistStamped`** **delta twists** on **`/servo_node/delta_twist_cmds`** (`moveit_servo.py`). That is how commanded velocities become Servo motion.

- **`ros_twist`** — **Custom teleoperator plugin** in **`lerobot-ros/lerobot_teleoperator_devices`** (`RosTwistTeleop`, `config_ros_twist.py`). It subscribes to **`geometry_msgs/Twist`** on the configured topic (default **`/game_controller`**, produced by `teleop_twist_joy` in the launch files). It does **not** talk to Servo directly; LeRobot combines its output with **`ur12e_ros`**, and the **robot** layer issues the **TwistStamped** Servo commands above.

So: **Twist** on `/game_controller` (teleop pipeline) → LeRobot **`ros_twist` + `ur12e_ros`** → **TwistStamped** on `/servo_node/delta_twist_cmds` (MoveIt Servo).

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
| `ursim_with_joy_teleop.launch.py` | **Main hardware / URSim entry:** UR driver + MoveIt + Servo + joy teleop stack |
| `ursim.launch.py`         | UR driver + MoveIt + Servo only (no bundled gamepad nodes) |
| `teleop_joy_for_lerobot.launch.py` | Gazebo-oriented joy + teleop_twist_joy + home_button_node (`use_sim_time`) |
| `teleop_joy_lerobot_ursim.py` | Same stack for hardware / URSim paths (name is historical; tune axes for your pad) |
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
