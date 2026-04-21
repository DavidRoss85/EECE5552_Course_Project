# UR12e — Imitation learning pipeline (fast path)

End-to-end path for **record → train → run policy** with LeRobot and this repo’s **`ur12e_ros`** stack. Use this as the main onboarding doc; deep dives stay in the linked files below.

---

## What you are setting up

| Stage | Tool | Role in this repo |
|-------|------|-------------------|
| **Record** | `lerobot-record` | Collect episodes (teleop and/or gaze + cameras) into a **local** dataset (`--dataset.root`). |
| **Train** | `lerobot-train` | Fit ACT (or another policy type) on that dataset; checkpoints under `outputs/train/...`. |
| **Evaluate / deploy** | `lerobot-record` + `--policy.path=...` | Run the trained policy on the robot while logging (example: `scripts/ur12e/start-act.sh`). |

Official LeRobot concepts: [Imitation learning on robots](https://huggingface.co/docs/lerobot/en/il_robots).

### Can a brand-new person bootstrap to success?

**Mostly yes, if they are comfortable editing shell flags and paths** — this repo is set up as a **course / research codebase**, not a shrink-wrapped product. You get working **patterns** (`lerobot-record` / `lerobot-train` / `lerobot-record` + policy), **explained custom pieces** (`ur12e_ros`, `ros_twist`, launches, gaze topics), and **checklists**, but you still need baseline familiarity with **ROS 2 Jazzy**, **MoveIt Servo**, and **LeRobot’s CLI** (official docs linked above).

**Use the right script trio together** (same machine, aligned `--dataset.root` / `--dataset.repo_id` / `--policy.path`):

| Track | Record | Train | Evaluate |
|-------|--------|-------|----------|
| **Gazebo / sim dataset** | [`record.sh`](../scripts/ur12e/record.sh) → `datasets/ur12e_sim_dataset` | [`train-act-sim.sh`](../scripts/ur12e/train-act-sim.sh) | [`eval-act-sim.sh`](../scripts/ur12e/eval-act-sim.sh) |
| **Lab gaze + cameras** | [`record_gaze.sh`](../scripts/ur12e/record_gaze.sh) (+ optional [`pub_coords.sh`](../scripts/ur12e/pub_coords.sh)) | [`train-act.sh`](../scripts/ur12e/train-act.sh) | [`start-act.sh`](../scripts/ur12e/start-act.sh) |

The top-level README table mixes **record** examples; **do not** point `train-act.sh` at the sim dataset unless you change its `--dataset.root` to match. **`train-act-sim.sh` in the repo is a minimal snippet** (it may end mid-command); treat it as the **exact training invocation the authors used** and **finish or adjust the `lerobot-train` line** (e.g. `batch_size`, `--dataset.episodes`, saving cadence) before you rely on it. **`eval-act-sim.sh`** expects a checkpoint path you trained; update `POLICY_DIR` if your run produced a different step folder.

If you do the **prereqs below**, bring up **sim + teleop** (or hardware + teleop), edit paths once, and fix the small script gaps above, you can **close the loop** without insider knowledge beyond normal ROS + LeRobot debugging.

---

## Prerequisites (do these once)

1. **ROS 2 Jazzy** sourced, workspace **built and sourced** (install **[`apt` packages for UR / MoveIt / Gazebo / joy first](#ros-packages-to-install-with-apt)** so `ros2 launch` can resolve upstream dependencies):
   ```bash
   cd ~/GitHub/EECE5552_Course_Project
   colcon build
   source install/setup.bash
   ```
2. **LeRobot CLI + this repo’s plugins** — install the **`lerobot-*`** command-line tools per **[Hugging Face — LeRobot installation](https://huggingface.co/docs/lerobot/installation)** (PyTorch, `ffmpeg`, `pip install lerobot`, etc.), then use the **`lerobot-ros`** Conda environment (full steps in the **[README](../README.md#conda-environment-for-lerobot-lerobot-ros)**). Short form:
   ```bash
   conda create -y -n lerobot-ros python=3.12
   conda activate lerobot-ros
   conda install -c conda-forge libstdcxx-ng -y
   source /opt/ros/jazzy/setup.bash
   cd ~/GitHub/EECE5552_Course_Project/lerobot-ros
   pip install --upgrade pip
   pip install -e lerobot_robot_ros lerobot_teleoperator_devices
   ```
   Each LeRobot terminal: `conda activate lerobot-ros`, then source **Jazzy** and **`install/setup.bash`**. More detail: [UR12E_LEROBOT.md](UR12E_LEROBOT.md#setup).
3. **Joystick teleop for `ros_twist`** (publishes `/game_controller`): Gazebo uses `launch/teleop_joy_for_lerobot.launch.py`; hardware / URSim combo uses `ursim_with_joy_teleop.launch.py`, which includes `launch/teleop_joy_lerobot_ursim.py` (**`ursim` in the filename is not simulator-only**). Both wrap `teleop_twist_joy` with defaults for an **older Xbox-style** controller—edit `enable_button` / `axis_linear.*` in those files and **test in Gazebo or URSim** before the real arm.
   ```bash
   source /opt/ros/jazzy/setup.bash
   source ~/GitHub/EECE5552_Course_Project/install/setup.bash
   ros2 launch launch/teleop_joy_for_lerobot.launch.py
   ```
4. **GPU** with CUDA for training and policy inference (`--policy.device=cuda` in the example scripts).

---

## ROS packages to install with apt

LeRobot and the local **`lerobot-ros`** wheels **do not** install the UR stack, MoveIt, Gazebo bridges, or joystick nodes for you. Those come from **ROS 2 Jazzy Debian packages** (and your lab’s bring-up for hardware). **`colcon build`** in this repo only builds **workspace packages** (e.g. `robot_control`, `perception`); it does not replace **`ros-jazzy-ur-robot-driver`**, **`ros-jazzy-moveit`**, etc.

| What you need | Debian packages (Jazzy) | Where it is used |
|----------------|-------------------------|------------------|
| **UR robot driver** (real arm or driver APIs) | `ros-jazzy-ur-robot-driver` | Hardware launches (`ursim.launch.py`, `ursim_with_joy_teleop.launch.py`), vendor docs |
| **Gazebo sim + UR in Gz** | `ros-jazzy-ur-simulation-gz`, `ros-jazzy-ros-gz-bridge` | `sim.launch.py`, [UR12E_GAZEBO_SETUP.md](UR12E_GAZEBO_SETUP.md) |
| **MoveIt 2** (planning + **MoveIt Servo**) | `ros-jazzy-moveit` | Simulation and hardware stacks used with this repo |
| **Joystick → `Twist`** (`joy_node`, `teleop_twist_joy`) | `ros-jazzy-joy`, `ros-jazzy-teleop-twist-joy` | `teleop_joy_for_lerobot.launch.py`, `teleop_joy_lerobot_ursim.py`, `teleop.launch.py` |

**Copy-paste bundle for Gazebo sim** (matches [simulation/README.md — Prerequisites](../simulation/README.md#ros-2-jazzy--gazebo-harmonic)):

```bash
sudo apt install ros-jazzy-moveit ros-jazzy-ur-simulation-gz ros-jazzy-ur-robot-driver \
  ros-jazzy-ros-gz-bridge ros-jazzy-joy ros-jazzy-teleop-twist-joy
```

**Physical UR12e:** at minimum **`ros-jazzy-ur-robot-driver`** plus whatever your MoveIt / controller integration expects—see [Universal Robots ROS 2 documentation](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/) and [README — Live UR12e](../README.md#live-ur12e-hardware). Install **`ros-jazzy-joy`** and **`ros-jazzy-teleop-twist-joy`** if you use the bundled joystick teleop launches.

**One-liner** (LeRobot joy stack only, if the rest is already installed): [UR12E_LEROBOT.md — ROS packages](UR12E_LEROBOT.md#1-ros-packages) (`sudo apt install ros-jazzy-joy ros-jazzy-teleop-twist-joy`).

**README** summary: [ROS system packages (apt)](../README.md#ros-system-packages-apt).

---

## Simulation vs real UR12e

| Topic | Simulation (fastest to validate pipeline) | Physical UR12e |
|-------|---------------------------------------------|----------------|
| **Bring-up** | `ros2 launch launch/sim.launch.py` (Gazebo + MoveIt + Servo). See [UR12E_GAZEBO_SETUP.md](UR12E_GAZEBO_SETUP.md), [simulation/README.md](../simulation/README.md). | **Main entry:** `ros2 launch launch/ursim_with_joy_teleop.launch.py robot_ip:=<controller IP>` — UR driver + MoveIt + Servo **and** joystick teleop (`/game_controller`). Driver-only: `ursim.launch.py` with the same `robot_ip`. This repo’s LeRobot examples assume **ROS image topics** and **MoveIt Servo** already work. |
| **Cameras** | Prefer `ros:///cameras/.../image_raw` matching your sim bridges. Example: `scripts/ur12e/record.sh`. | Same **ROS URI** style if you publish calibrated images to fixed topic names; or **`/dev/videoN`** OpenCV paths (see `record_gaze.sh`). Tune devices with `v4l2-ctl --list-devices` / `ros2 topic list`. |
| **Safety** | Lower stakes. | Use reduced speed, clear workspace, e-stop ready, follow lab procedures. |

**Important:** [UR12E_LEROBOT.md](UR12E_LEROBOT.md) is written around **Gazebo** first; this file adds the **real-robot** column and ties scripts together.

---

## Stage 1 — Record data (`lerobot-record`)

### Example scripts (copy paths / topics before you run)

| Script | Purpose |
|--------|---------|
| [`scripts/ur12e/record.sh`](../scripts/ur12e/record.sh) | Sim-oriented: three **ROS** cameras, teleop-only, dataset under `datasets/ur12e_sim_dataset`. |
| [`scripts/ur12e/record_gaze.sh`](../scripts/ur12e/record_gaze.sh) | **Real / lab-style:** gaze defaults + `ros:///cameras/front/image_raw` + **USB** side/gripper cameras; dataset under `datasets/ur12e_gaze_with_gripper`. |
| [`scripts/ur12e/pub_coords.sh`](../scripts/ur12e/pub_coords.sh) | Runs **`perception` `vla_detector`** on **`/cameras/front/image_raw`** → publishes **`/vla/coords`** for gaze scripts (`gaze_topic_name=/vla/coords`). Optional arg: **`red`** (default), **`blue`**, **`yellow`** to target that cube color. Same text as the script header. |

**Run with bash** (scripts use env expansion):

```bash
chmod +x scripts/ur12e/record.sh scripts/ur12e/record_gaze.sh
# Sim example
./scripts/ur12e/record.sh

# Gaze example — pass default gaze pixel x y (used until live gaze updates)
bash scripts/ur12e/record_gaze.sh 320 240

# Optional: in another terminal, stream cube centers to /vla/coords for gaze conditioning
bash scripts/ur12e/pub_coords.sh        # default: red cube
bash scripts/ur12e/pub_coords.sh blue   # blue cube only
```

**You must edit** inside each script:

- `--dataset.repo_id` / `--dataset.root` (where LeRobot writes episodes).
- `--robot.cameras` (topic names and `/dev/video*` indices **on your machine**).
- `--dataset.num_episodes`, `--dataset.episode_time_s`, task string.

**Teleop:** keep **`--teleop.type=ros_twist`** and run the joy launch for your stack (**`teleop_joy_for_lerobot`** in sim, or **`teleop_joy_lerobot_ursim`** when bundled with hardware/URSim); hold whatever **`enable_button`** maps to (default **RB** on the stock Xbox-style mapping—change the launch file if your pad differs). See [UR12E_LEROBOT.md](UR12E_LEROBOT.md#joystick-mapping).

**Teleop-only smoke test:** `ursim_with_joy_teleop.launch.py` with the right **`robot_ip`**, then **`lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist`**. **`ur12e_ros`** is this repo’s custom **robot** plugin in `lerobot-ros`; **`ros_twist`** is the custom **teleop** plugin that reads **`Twist`** on **`/game_controller`**, while **`ur12e_ros`** sends **`TwistStamped`** delta velocities to MoveIt Servo on **`/servo_node/delta_twist_cmds`**. Details: [UR12E_LEROBOT.md](UR12E_LEROBOT.md#custom-plugins-and-moveit-servo-control-path), [README](../README.md#smoke-test-teleop-only-lerobot).

**Resume:** `--resume true` continues an existing dataset at the same `--dataset.root`; use `false` or a fresh directory for a clean run.

---

## Key nodes, launches, and helper scripts

This table is the **discovery index** for the repo: it repeats the **intent** of module docstrings and file headers so newcomers see it in **docs** first. When you change behavior in code, update the matching row here and in the **[README — Repo map](../README.md#repo-map)**.

| Piece | Location | Summary (matches source headers) |
|-------|----------|-----------------------------------|
| Driver + joystick teleop | [`launch/ursim_with_joy_teleop.launch.py`](../launch/ursim_with_joy_teleop.launch.py) | Main entry: includes `ursim.launch.py` + `teleop_joy_lerobot_ursim.py`; `robot_ip` = UR controller (**live arm or URSim**). **`ursim` in the path is a misnomer**; name kept (actually used). |
| Driver only | [`launch/ursim.launch.py`](../launch/ursim.launch.py) | UR driver + MoveIt + Servo; no bundled joy. Same **misnomer**—works on **hardware** with `robot_ip`; filenames unchanged (actually used). |
| Joy → `/game_controller` (Gazebo) | [`launch/teleop_joy_for_lerobot.launch.py`](../launch/teleop_joy_for_lerobot.launch.py) | `joy_node` + `teleop_twist_joy` + `home_button_node`; `use_sim_time`; tune axes for your gamepad. |
| Joy → `/game_controller` (hardware / URSim) | [`launch/teleop_joy_lerobot_ursim.py`](../launch/teleop_joy_lerobot_ursim.py) | Same stack; filename `ursim` is historical. |
| B → home (ROS only) | [`src/robot_control/robot_control/home_button_node.py`](../src/robot_control/robot_control/home_button_node.py) | Trajectory to `HOME_JOINTS`; not a LeRobot training action; see [UR12E_LEROBOT — Joystick](UR12E_LEROBOT.md#joystick-mapping). |
| `/vla/coords` publisher | [`scripts/ur12e/pub_coords.sh`](../scripts/ur12e/pub_coords.sh) → `vla_detector` | HSV detection on front camera topic → `Float32MultiArray` gaze pixels for `record_gaze.sh` / `start-act.sh`; color arg `red` / `blue` / `yellow`. |
| LeRobot UR stack | [`lerobot-ros/`](../lerobot-ros/) | Custom **`ur12e_ros`** robot + **`ros_twist`** teleop; see [UR12E_LEROBOT — Custom plugins…](UR12E_LEROBOT.md#custom-plugins-and-moveit-servo-control-path). |

**`ursim*.launch.py` naming:** [`ursim.launch.py`](../launch/ursim.launch.py) and [`ursim_with_joy_teleop.launch.py`](../launch/ursim_with_joy_teleop.launch.py) suggest simulator-only workflows; in practice they target **whatever UR controller** you pass as **`robot_ip`** (**physical arm or URSim**). The repo **does not rename** them—these paths are what was **actually used**; see also the [README — Repo map](../README.md#repo-map) footnote.

---

## Stage 2 — Train (`lerobot-train`)

Canonical example: [`scripts/ur12e/train-act.sh`](../scripts/ur12e/train-act.sh).

It runs **`lerobot-train`** with:

- `--dataset.root` pointing at the **same** tree you recorded into.
- `--policy.type=act`, `--output_dir`, `--job_name`, `--steps`, etc.

**Episode subset:** the checked-in `train-act.sh` includes a long `--dataset.episodes="[...]"` list from one project run. **Newcomers should** either:

- Remove `--dataset.episodes=...` to train on **all** episodes (if your LeRobot version supports that), or  
- Replace the list with **`[0, 1, ..., N-1]`** for your **N** episodes (see `meta/info.json` → `total_episodes` in the dataset).

```bash
bash scripts/ur12e/train-act.sh
```

Training time depends on `--steps`, GPU, and dataset size. For methodology notes and wandb/hub toggles, see [SO101_IMITATION_LEARNING.md](SO101_IMITATION_LEARNING.md) (SO101 POC, same LeRobot tools).

---

## Stage 3 — Run a trained policy (`lerobot-record` + policy)

Example: [`scripts/ur12e/start-act.sh`](../scripts/ur12e/start-act.sh).

- **`--policy.path=.../pretrained_model`** loads the checkpoint.
- Still uses **`--robot.type=ur12e_ros`**, cameras, gaze topic, and **`--teleop.type=ros_twist`** so you can recover / nudge with the stick depending on your LeRobot version and flags.
- **`$1` / `$2`** are gaze default x/y when something (e.g. dwell UI) invokes the script with coordinates.

Edit **`--dataset.root`**, **`--dataset.repo_id`**, **`--policy.path`**, **`--resume`**, and camera lines for your eval run.

```bash
bash scripts/ur12e/start-act.sh 320 240
```

---

## Other useful scripts in `scripts/ur12e/`

| Script | Notes |
|--------|--------|
| `train-smolvla.sh` | Train SmolVLA instead of ACT. |
| `start-smolvla.sh` | Run SmolVLA checkpoint. |
| `eval-act-sim.sh` / `train-act-sim.sh` | Sim-oriented variants. |
| `remove_episode.sh` | Dataset maintenance. |
| `pub_coords.sh` | Also listed under **Stage 1** and **[Key nodes…](#key-nodes-launches-and-helper-scripts)** — `vla_detector` → `/vla/coords`. |

---

## Python environment gotchas (dwell / pygame / EyeGestures)

ROS-installed nodes often use **`/usr/bin/python3`**. If you prepend a **venv** to `PYTHONPATH` for EyeGestures, keep **`numpy<2`** in that venv so **`cv_bridge`** (ROS Jazzy) does not break. See project discussions and [UR12E_LEROBOT.md](UR12E_LEROBOT.md) for conda/pip layout.

---

## Where to go next

| Need | Doc |
|------|-----|
| LeRobot + sim + `ros_twist` detail | [UR12E_LEROBOT.md](UR12E_LEROBOT.md) |
| Joystick, B-home, gripper quirks | [UR12E_TELEOP.md](UR12E_TELEOP.md), [UR12E_TELEOP_GRIPPER_SETUP.md](UR12E_TELEOP_GRIPPER_SETUP.md) |
| Joints / MoveIt group | [UR12E_REFERENCE.md](UR12E_REFERENCE.md) |
| Gazebo install | [UR12E_GAZEBO_SETUP.md](UR12E_GAZEBO_SETUP.md) |
| Record → train narrative (different robot, same tools) | [SO101_IMITATION_LEARNING.md](SO101_IMITATION_LEARNING.md) |
| Dwell + VLA trigger | [DWELL_DEMO.md](DWELL_DEMO.md), [EYEGAZE_SETUP.md](EYEGAZE_SETUP.md) |
| What each launch / script / key node does (same text as file headers) | [README — Repo map](../README.md#repo-map), **[Key nodes…](#key-nodes-launches-and-helper-scripts)** (this doc) |
| UR / MoveIt / Gazebo / joy `apt` packages | **[ROS packages to install with apt](#ros-packages-to-install-with-apt)** (this doc), [README — ROS system packages (apt)](../README.md#ros-system-packages-apt) |

---

## Checklist (minimum before first real recording)

- [ ] **[ROS `apt` packages](#ros-packages-to-install-with-apt)** for your path (sim vs hardware) are installed so `ros2 launch` resolves `ur_*`, MoveIt, `joy`, and `teleop_twist_joy`.
- [ ] MoveIt Servo moves the arm from `/game_controller` with teleop alone (no LeRobot).
- [ ] If you use **`record_gaze.sh`** / gaze-conditioned eval, **`/vla/coords`** is publishing (e.g. **`pub_coords.sh`** or your dwell stack) and matches **`gaze_topic_name`** in the script.
- [ ] Camera topics (or USB devices) match `--robot.cameras` in your script.
- [ ] `lerobot-record --help` matches flags you use (LeRobot version drift).
- [ ] Dataset directory has enough disk space; `--dataset.push_to_hub=false` keeps data local.

When in doubt, **record one short episode in sim** (`record.sh`), **train a tiny ACT** on it, then **run `start-act.sh` pointed at that checkpoint** to prove the loop before using the real arm.
