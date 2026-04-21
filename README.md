# EECE5552 Course Project

**Primary deliverable — UR12e imitation learning (LeRobot):** record demonstrations on the UR12e (sim or hardware), train policies (e.g. ACT), and run trained checkpoints on the robot. Everything else in the repo supports that pipeline. **New here?** Skim **[Repo map](#repo-map)** (same roles as the comments in `launch/`, `scripts/`, and key `src/` nodes) then **[docs/UR12E_IL_PIPELINE.md](docs/UR12E_IL_PIPELINE.md)**.

<a id="documentation-disclaimer"></a>

**Documentation disclaimer:** Parts of this **README** and of the **`docs/`** tree were written or revised with **AI assistance**. Be mindful that **commands, package names, paths, and explanations can occasionally be wrong or hallucinated**—cross-check against the **source code**, **launch files**, **scripts you actually run**, and **official** [LeRobot](https://huggingface.co/docs/lerobot) / [ROS 2](https://docs.ros.org/en/jazzy/) / [Universal Robots ROS 2](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/) documentation before depending on them (especially on **real hardware**). **Regardless of what the docs say, the codebase was left as-is at project completion—`src/`, `launch/`, `lerobot-ros/`, and the checked-in scripts are the source of truth**; treat Markdown as orientation, not a spec.

---

## Imitation learning pipeline (start here)

| Step | What to run | Example in repo |
|------|-------------|-----------------|
| **1. Record** | `lerobot-record` with `ur12e_ros` + `ros_twist` | [`scripts/ur12e/record_gaze.sh`](scripts/ur12e/record_gaze.sh) (gaze + cameras), [`scripts/ur12e/record.sh`](scripts/ur12e/record.sh) (sim / ROS cameras) |
| **2. Train** | `lerobot-train` on your dataset | [`scripts/ur12e/train-act.sh`](scripts/ur12e/train-act.sh) |
| **3. Deploy / eval** | `lerobot-record` + `--policy.path=...` | [`scripts/ur12e/start-act.sh`](scripts/ur12e/start-act.sh) (hardware / gaze-style); sim: [`scripts/ur12e/eval-act-sim.sh`](scripts/ur12e/eval-act-sim.sh) |

**Match scripts to the same track:** sim data → [`record.sh`](scripts/ur12e/record.sh) + [`train-act-sim.sh`](scripts/ur12e/train-act-sim.sh) + [`eval-act-sim.sh`](scripts/ur12e/eval-act-sim.sh). Lab gaze data → [`record_gaze.sh`](scripts/ur12e/record_gaze.sh) + [`train-act.sh`](scripts/ur12e/train-act.sh) + [`start-act.sh`](scripts/ur12e/start-act.sh). You are expected to edit paths, `repo_id`, checkpoints, and sometimes **complete** a minimal training snippet—see **[“Can a brand-new person bootstrap…?”](docs/UR12E_IL_PIPELINE.md#can-a-brand-new-person-bootstrap-to-success)** in the pipeline doc.

**Full walkthrough (prereqs, sim vs real arm, paths to edit, checklist):**  
**[docs/UR12E_IL_PIPELINE.md](docs/UR12E_IL_PIPELINE.md)**

LeRobot + `ur12e_ros` plugin setup, joystick mapping, and recording details: **[docs/UR12E_LEROBOT.md](docs/UR12E_LEROBOT.md)**

---

## Repo map

**If you are new here, read this section first** — it mirrors the **comments and module docstrings** in `scripts/`, `launch/`, and selected `src/` nodes so you do not have to grep the tree to learn roles. The same table (with file pointers) lives in **[docs/UR12E_IL_PIPELINE.md — Key nodes, launches, and helper scripts](docs/UR12E_IL_PIPELINE.md#key-nodes-launches-and-helper-scripts)**.

| What | Where | Role |
|------|--------|------|
| **Driver + joystick teleop** | [`launch/ursim_with_joy_teleop.launch.py`](launch/ursim_with_joy_teleop.launch.py) | **Main UR bring-up (live arm or URSim):** UR driver + MoveIt + Servo + `joy_node` + `teleop_twist_joy` → `/game_controller` + `home_button_node`. **Filename is a misnomer**—see naming note below. Docstring in file. |
| **Driver only** | [`launch/ursim.launch.py`](launch/ursim.launch.py) | Same stack **without** bundled gamepad nodes; use when teleop is launched separately. **Also a misnomer** (`ursim`); works on the **live robot** via `robot_ip`. Names kept as-is (what the lab actually used). Docstring in file. |
| **LeRobot joy stack (Gazebo)** | [`launch/teleop_joy_for_lerobot.launch.py`](launch/teleop_joy_for_lerobot.launch.py) | `use_sim_time`, `/game_controller`; tune **`teleop_twist_joy`** axes for your pad. Header comment in file. |
| **LeRobot joy stack (hardware path)** | [`launch/teleop_joy_lerobot_ursim.py`](launch/teleop_joy_lerobot_ursim.py) | Same nodes as above for real arm / URSim combo; **`ursim` in the name is historical**. Header comment in file. |
| **B → ROS home** | [`src/robot_control/robot_control/home_button_node.py`](src/robot_control/robot_control/home_button_node.py) | **Not** the LeRobot action stream; fixed-time home trajectory—see [UR12E_LEROBOT — Joystick](docs/UR12E_LEROBOT.md#joystick-mapping). Module docstring + `HOME_JOINTS` comment in file. |
| **Gaze / cube pixels → `/vla/coords`** | [`scripts/ur12e/pub_coords.sh`](scripts/ur12e/pub_coords.sh) → `perception` **`vla_detector`** | Subscribes **`/cameras/front/image_raw`**, publishes **`/vla/coords`** for **`record_gaze.sh` / `start-act.sh`** (`gaze_topic_name=/vla/coords`). First arg **`red`** (default), **`blue`**, or **`yellow`**. Script header + [`vla_detector.py`](src/perception/perception/nodes/vla_detector.py) module docstring. |

**Naming (`ursim` launches):** [`launch/ursim.launch.py`](launch/ursim.launch.py) and [`launch/ursim_with_joy_teleop.launch.py`](launch/ursim_with_joy_teleop.launch.py) **sound URSim-only**, but both drive the **real UR12e** when you pass the **physical controller’s `robot_ip`** (they are the same driver + MoveIt + Servo stack you used on hardware). **Filenames are left unchanged** on purpose—these exact paths are what was **actually run** in the project; renaming would break muscle memory and old notes.

---

## ROS system packages (apt)

Conda installs **LeRobot**; **`colcon build`** installs **this repo’s** packages. You still need **upstream ROS 2 Jazzy binaries** on Ubuntu: **UR driver** (`ros-jazzy-ur-robot-driver`), **MoveIt** (`ros-jazzy-moveit`), **Gazebo sim + bridge** (`ros-jazzy-ur-simulation-gz`, `ros-jazzy-ros-gz-bridge`) for simulation, and **`joy` + `teleop_twist_joy`** (`ros-jazzy-joy`, `ros-jazzy-teleop-twist-joy`) for the joystick launches used with `ros_twist`.

**Full table, copy-paste apt lines, and sim vs hardware notes:** **[docs/UR12E_IL_PIPELINE.md — ROS packages to install with apt](docs/UR12E_IL_PIPELINE.md#ros-packages-to-install-with-apt)** (also summarized in [simulation/README.md](simulation/README.md) and [docs/UR12E_GAZEBO_SETUP.md](docs/UR12E_GAZEBO_SETUP.md)).

---

## Conda environment for LeRobot (`lerobot-ros`)

Use a dedicated Conda env so **`lerobot-record`**, **`lerobot-train`**, and the **`ur12e_ros` / `ros_twist`** plugins share one Python stack (CUDA-friendly, separate from the system ROS Python).

You must have the **LeRobot CLI** installed—the **`lerobot-record`**, **`lerobot-train`**, **`lerobot-teleoperate`**, and related commands this repo’s scripts call. Official setup (Python, PyTorch, `ffmpeg`, `pip install lerobot`, optional extras) is in the Hugging Face docs: **[LeRobot — Installation](https://huggingface.co/docs/lerobot/installation)** and overview **[LeRobot documentation](https://huggingface.co/docs/lerobot)**. Follow that guidance for CUDA/PyTorch versions on your machine; then add this repo’s plugins in the steps below.

**Requirements:** [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda, **ROS 2 Jazzy** installed at `/opt/ros/jazzy`, and this repo cloned locally.

```bash
# 1) Create env (Python 3.12 matches ROS Jazzy / common wheels)
conda create -y -n lerobot-ros python=3.12
conda activate lerobot-ros

# 2) C++ standard library from conda-forge (helps some PyTorch / wheel builds on Linux)
conda install -c conda-forge libstdcxx-ng -y

# 3) ROS in this shell (needed for rclpy when using the plugins)
source /opt/ros/jazzy/setup.bash

# 4) Install Hugging Face LeRobot + this repo’s ROS plugins (editable)
cd ~/GitHub/EECE5552_Course_Project/lerobot-ros
pip install --upgrade pip
pip install -e lerobot_robot_ros lerobot_teleoperator_devices
```

Installing **`lerobot_robot_ros`** pulls the **`lerobot`** package as a dependency (see `lerobot-ros/lerobot_robot_ros/pyproject.toml`), which normally registers the **CLI entry points**. Verify with **`which lerobot-record`** and **`lerobot-record --help`**. If those commands are missing or you need extras (PyTorch build, `ffmpeg`, etc.), install or repair LeRobot per **[the official installation guide](https://huggingface.co/docs/lerobot/installation)** (e.g. **`pip install lerobot`** or **`pip install -e .`** from a cloned [huggingface/lerobot](https://github.com/huggingface/lerobot) tree), then re-run the **`pip install -e lerobot_robot_ros ...`** line above.

**Every terminal** where you run LeRobot against the robot should:

1. `conda activate lerobot-ros`
2. `source /opt/ros/jazzy/setup.bash`
3. `source ~/GitHub/EECE5552_Course_Project/install/setup.bash` (workspace overlays, e.g. `robot_control`)

**Remove / recreate the env** if you need a clean slate:

```bash
conda deactivate
conda env remove -n lerobot-ros -y
# then repeat the create/install steps above
```

---

## Live UR12e (hardware)

Use this when the **physical** arm and controller are on the network (not Gazebo). The same LeRobot scripts apply once ROS can move the real robot and your camera topics or USB devices match the script.

### Before you run anything

1. **Network** — Workstation and UR **controller** (teach pendant network) can reach each other. Note the controller’s **IP address** (robot side).
2. **ROS packages** — Install and build what your lab uses for **UR12e + MoveIt + Servo** (same family of packages as simulation; see [docs/UR12E_GAZEBO_SETUP.md](docs/UR12E_GAZEBO_SETUP.md) for related apt installs and [Universal Robots ROS 2 documentation](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/) for the driver).
3. **Workspace** — From the repo root: `colcon build`, then `source install/setup.bash` in every terminal.

### Bring up the arm stack

**Primary entry point (UR12e driver + joystick teleop):** [`launch/ursim_with_joy_teleop.launch.py`](launch/ursim_with_joy_teleop.launch.py) starts the **UR ROS 2 driver** + **MoveIt** + **Servo** and, in the same process tree, **`joy_node`**, **`teleop_twist_joy`** (→ `/game_controller`), and **`home_button_node`**. Use this for hardware or URSim when you want gamepad Servo teleop without launching teleop in a second terminal. Pass **`robot_ip`** as the **UR controller** address (real arm or simulator).

```bash
source /opt/ros/jazzy/setup.bash
source ~/GitHub/EECE5552_Course_Project/install/setup.bash

ros2 launch launch/ursim_with_joy_teleop.launch.py robot_ip:=<CONTROLLER_IP>
```

**Driver only (no bundled joystick):** [`launch/ursim.launch.py`](launch/ursim.launch.py) is the same driver + MoveIt + Servo stack **without** the joy nodes—use it if you start teleop elsewhere or do not need a gamepad.

```bash
ros2 launch launch/ursim.launch.py robot_ip:=<CONTROLLER_IP>
```

Example IP pattern: [`scripts/ur12e/launch_nodes.sh`](scripts/ur12e/launch_nodes.sh).

### Sanity checks before LeRobot

- **`/joint_states`** updates when the arm moves: `ros2 topic echo /joint_states --once`
- **Joystick + Servo** — With teleop running, **hold RB** (deadman) and move sticks; the real arm should follow slowly and predictably. If not, fix teleop/Servo before `lerobot-record`.
- **B button** — Sends the arm to **ROS home** via `home_button_node`; that move is **not** reflected in the LeRobot / ML action stream, and it can be **fast in joint space** if you start far from home—see [UR12E_LEROBOT.md](docs/UR12E_LEROBOT.md#joystick-mapping) for warnings and home joint angles (degrees).
- **Cameras** — Point your record script at **live** sources: `ros:///...` topics your nodes publish, and/or **`/dev/videoN`** paths (see [`scripts/ur12e/record_gaze.sh`](scripts/ur12e/record_gaze.sh)). Use `v4l2-ctl --list-devices` / `ros2 topic list` to match your bench.

### Smoke test: teleop only (LeRobot)

To **try joystick teleop through LeRobot** without recording: start the stack with the **correct `robot_ip`**, then run **`lerobot-teleoperate`** with this repo’s plugin types.

1. **ROS + driver + joy** (one terminal), from a sourced workspace:
   ```bash
   source /opt/ros/jazzy/setup.bash
   source ~/GitHub/EECE5552_Course_Project/install/setup.bash
   ros2 launch launch/ursim_with_joy_teleop.launch.py robot_ip:=<CONTROLLER_IP>
   ```
2. **LeRobot** (second terminal), Conda env + Jazzy, then:
   ```bash
   conda activate lerobot-ros
   source /opt/ros/jazzy/setup.bash
   lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist
   ```

**What those CLI flags are** — both are **custom plugins shipped in this repo’s `lerobot-ros/` tree**, not generic upstream LeRobot identifiers:

- **`ur12e_ros`** — Custom **robot** interface (`lerobot_robot_ros`: `UR12eROS` / `ROS2Robot` in `config.py` + `robot.py`). It wires the UR12e to **MoveIt Servo** by publishing **`geometry_msgs/TwistStamped`** **delta velocity** commands on **`/servo_node/delta_twist_cmds`** (see `moveit_servo.py`).
- **`ros_twist`** — Custom **teleoperator** (`lerobot_teleoperator_devices`: `RosTwistTeleop` in `ros_twist.py`). It subscribes to **`geometry_msgs/Twist`** on **`/game_controller`** (from `teleop_twist_joy` in the launch file). LeRobot passes that twist into the robot plugin, which converts it into the **TwistStamped** stream Servo expects.

Hold your mapped deadman (default **RB** on the stock Xbox-style mapping) and move the sticks; the arm should jog. Full context: [UR12E_LEROBOT.md](docs/UR12E_LEROBOT.md#custom-plugins-and-moveit-servo-control-path).

### Record / train / policy on hardware

Same three steps as in the table above; edit **`--robot.cameras`**, **`--dataset.root`**, and **`--policy.path`** for your machine. Gripper / secondary tooling may use a separate port (see [docs/UR12E_TELEOP_GRIPPER_SETUP.md](docs/UR12E_TELEOP_GRIPPER_SETUP.md)).

### Safety

Use reduced speeds, a clear workspace, and your lab’s **e-stop** and supervision procedures. Treat the first policy runs as **commissioning**, not production.

---

## ROS 2 stack (simulation and teleop)

ROS 2 **Jazzy**. Use this block when you need Gazebo + MoveIt + Servo or joystick teleop without LeRobot.

```bash
# Build (minimal package for teleop helpers)
colcon build --packages-select robot_control
source install/setup.bash

# Simulation (~30 s to full startup)
ros2 launch launch/sim.launch.py

# Joystick teleop (standalone)
ros2 launch launch/teleop.launch.py
```

For **LeRobot** recording, use **`teleop_joy_for_lerobot.launch.py`** in Gazebo (publishes `/game_controller`) or the same stack from **`teleop_joy_lerobot_ursim.py`** when using **`ursim_with_joy_teleop.launch.py`** / hardware—the **`ursim` name is historical**; that file is not simulator-only. **`teleop_twist_joy` axis and deadman indices** in those launch files target an **older Xbox-style** pad; expect to edit them and **verify in Gazebo or URSim** before the live robot. See [UR12E_LEROBOT.md](docs/UR12E_LEROBOT.md) (Run → Terminal 2 and gamepad note).

---

## Data, eval runs, and models (Hugging Face)

Published **datasets**, **eval logs**, and **checkpoints** from the course project (see [disclaimer](#documentation-disclaimer)—verify against your local runs).

There is **no `datasets/` or `data/` tree checked into this repository**: raw LeRobot episode data and eval exports are **far too large for GitHub**. The example scripts still use local paths such as `datasets/...` and `eval_datasets/...` on your machine when you **record** or **evaluate**; treat the links below (and your own disk) as where the bulky artifacts actually live.

| Artifact | Link | Notes |
|----------|------|--------|
| **Eval dataset (primary)** | [frazier-z/eval_ur12_act](https://huggingface.co/datasets/frazier-z/eval_ur12_act) | Main real-robot eval run; roughly **20–30%** success rate reported (**3 / 13** successes). |
| **Eval dataset (camera sweep)** | [frazier-z/eval_ur12_act_v2](https://huggingface.co/datasets/frazier-z/eval_ur12_act_v2) | **24** re-evals while tuning camera angles; **no** successes in that series. |
| **ACT checkpoint (demo)** | [frazier-z/ur12e-act-v2](https://huggingface.co/frazier-z/ur12e-act-v2) | Final **ACT** policy—the one used in the **demo video**. |
| **SmolVLA checkpoint** | [frazier-z/smolvla_ur12e_gaze_with_gripper_v5](https://huggingface.co/frazier-z/smolvla_ur12e_gaze_with_gripper_v5) | Final **SmolVLA** model (“Mr. Krabs”). |
| **Diffusion checkpoint** | [frazier-z/ur12e-diffusion](https://huggingface.co/frazier-z/ur12e-diffusion) | Final **diffusion** policy; strong **retry** behavior. |
| **Training data (videos)** | [ur12e_gaze_with_gripper — top camera chunks](https://huggingface.co/datasets/frazier-z/ur12e_gaze_with_gripper/tree/main/videos/observation.images.top/chunk-000) | **~290**-episode gaze + gripper dataset (observation video branch). |

### Demo videos (local files)

Edited **screen captures** for the write-up (paths are **relative to the repo root**; they resolve when the files exist in your checkout—often **not** on GitHub if you keep binaries local). See [`videos/README.md`](videos/README.md) for the expected names.

| Clip | Local file | What it shows |
|------|------------|----------------|
| **ACT (success)** | [`videos/act_combined.mp4`](videos/act_combined.mp4) | Successful **real-robot** eval of the **ACT** policy. |
| **Diffusion (success + retries)** | [`videos/diffusion_combined_grasp_portion.mp4`](videos/diffusion_combined_grasp_portion.mp4) | Successful **diffusion** eval; highlights the more elaborate **retry** behavior around the grasp. |
| **SmolVLA (gripper quirk)** | [`videos/smolvla_eval.mp4`](videos/smolvla_eval.mp4) | **SmolVLA** eval: fails to secure the grasp and **cycles the gripper** repeatedly (odd failure mode). |
| **Sim pipeline validation** | [`videos/simulated_grab.mp4`](videos/simulated_grab.mp4) | **Gazebo** pick-ups recorded while **validating** the ML pipeline in sim. |

---

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/UR12E_IL_PIPELINE.md](docs/UR12E_IL_PIPELINE.md) | **Deliverable hub:** record → train → policy (sim + real); **ROS `apt` packages** (UR driver, MoveIt, joy, teleop, Gazebo); **Key nodes, launches, and helper scripts** |
| [docs/UR12E_LEROBOT.md](docs/UR12E_LEROBOT.md) | LeRobot + `ur12e_ros` + `ros_twist`, cameras, troubleshooting |
| [simulation/README.md](simulation/README.md) | Simulation setup, launch order, goal-based control |
| [docs/UR12E_TELEOP.md](docs/UR12E_TELEOP.md) | Joystick teleop, B-button home, mapping |
| [docs/UR12E_TELEOP_GRIPPER_SETUP.md](docs/UR12E_TELEOP_GRIPPER_SETUP.md) | Teleop + gripper wiring and debug |
| [docs/SO101_IMITATION_LEARNING.md](docs/SO101_IMITATION_LEARNING.md) | SO101 imitation learning POC (same LeRobot tools) |
| [docs/UR12E_GAZEBO_SETUP.md](docs/UR12E_GAZEBO_SETUP.md) | UR simulator installation (apt) |
| [docs/UR12E_REFERENCE.md](docs/UR12E_REFERENCE.md) | Joint names, planning group, upstream UR docs |
| [docs/MOVEIT_PUBLISHER_NODE.md](docs/MOVEIT_PUBLISHER_NODE.md) | MoveIt publisher node |

Other topics (gaze / VLA dwell, perception nodes): see the `docs/` directory.
