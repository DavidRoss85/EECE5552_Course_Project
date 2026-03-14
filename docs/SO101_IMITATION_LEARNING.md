# SO101 Imitation Learning POC (Prior to UR12e)

This document describes how I performed imitation learning on the SO-101 robotic arm as a **proof of concept** before attempting it on the UR12e. It is not a general guide for SO101 imitation training—it records the setup and workflow I used to validate the LeRobot pipeline (record → train → evaluate) on a low-cost arm first.

Sources consulted:

- **[TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100)** — Open-source arm design, BOM, 3D printing
- **[Hugging Face LeRobot: Imitation Learning on Real-World Robots](https://huggingface.co/docs/lerobot/en/il_robots)** — IL workflow
- **[Hugging Face LeRobot: SO-101](https://huggingface.co/docs/lerobot/en/so101)** — SO101 assembly and setup
- **[Seeed Studio: SoArm in LeRobot](https://wiki.seeedstudio.com/lerobot_so100m_new/)** — SO100/SO101 hardware and calibration

---

## Overview

The SO-101 uses a **leader–follower** configuration: the leader arm is moved by hand for teleoperation; the follower performs the task. I used [LeRobot](https://github.com/huggingface/lerobot) to record (observation, action) pairs during teleoperation, train ACT and SmolVLA policies, and evaluate them. This POC validated the pipeline before applying it to the UR12e.

---

## How Imitation Learning with LeRobot Works (Recording Loop)

This section describes the recording process I used. The SO-101 was in its home position with a camera pointed at it. I ran `record.sh` (configured for 30-second episodes and a 30-second reset time, 5 episodes per run).

**Per episode:**

1. **Audio from the laptop**: "Started recording."
2. **Teleoperate**: Move the leader arm so the follower picks up the block, places it in the basket, then returns to its resting position.
3. **Audio from the laptop**: "Reset the environment."
4. **Reset**: Pick the block up from the basket and put it back in front of the SO-101 arm.
5. **Audio from the laptop**: "Started recording."
6. **Repeat** for the next episode.

After 5 episodes, the run finishes (since `record.sh` is configured for 5 episodes). To collect more, run `record.sh` again with `--resume true` so it appends to the same dataset.

LeRobot records camera frames (observations) and joint positions/actions in sync. The trained policy learns to map observations to actions so the robot can repeat the task autonomously.

---

## Pipeline Summary (POC Workflow)

| Step | Purpose |
|------|---------|
| 1. Source parts & 3D print | [SO-ARM100 GitHub](https://github.com/TheRobotStudio/SO-ARM100) — BOM, STL files |
| 2. Install LeRobot + Feetech | `pip install -e ".[feetech]"` |
| 3. Configure motors | Set unique IDs and baudrate per motor |
| 4. Assemble | Leader and follower arms |
| 5. Calibrate | Align leader and follower position mapping |
| 6. Teleoperate | Practice the task with leader → follower |
| 7. Record dataset | Capture (observation, action) with cameras |
| 8. Train policy | ACT, SmolVLA, or other policy types |
| 9. Evaluate | Run inference and record success rate |

---

The following sections describe the steps I followed for the SO101 POC (hardware, setup, recording, training, evaluation). **My Setup and Workflow** at the end summarizes my exact commands and scripts.

---

## 1. Hardware Source (SO-ARM100 GitHub)

The [SO-ARM100 repository](https://github.com/TheRobotStudio/SO-ARM100) provides:

- Bill of materials (BOM) for sourcing parts
- 3D printing STL files (Follower and Leader)
- Assembly and wiring instructions

SO-101 is the successor to SO-100 with updated wiring and leader-arm gear ratios. SO100/SO101 share the same LeRobot integration; the calibration and motor setup differ slightly (see Seeed Studio spec tables).

---

## 2. Install LeRobot

```bash
# Create conda env
conda create -y -n lerobot python=3.10 && conda activate lerobot

# Clone and install LeRobot with Feetech (required for SO101)
git clone https://github.com/huggingface/lerobot.git ~/lerobot
cd ~/lerobot && pip install -e ".[feetech]"
```

On Jetson, follow the [Seeed Studio environment setup](https://wiki.seeedstudio.com/lerobot_so100m_new/#install-lerobot) for PyTorch/CUDA and ffmpeg.

---

## 3. Configure Motors

### Find USB ports

```bash
lerobot-find-port
```

Disconnect each arm when prompted to identify leader vs follower ports (e.g. `/dev/so101_follower`, `/dev/so101_leader`, or raw `/dev/ttyACM0`, `/dev/ttyACM1` before udev rules).

### Set motor IDs and baudrate

Connect each motor one at a time and run:

**Follower:**
```bash
lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/so101_follower
```

**Leader:**
```bash
lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port=/dev/so101_leader
```

Follow the on-screen instructions to assign IDs 1–6 (gripper = 6, then wrist_roll, etc.).

---

## 4. Assemble

Assembly steps are documented with images in:

- [Hugging Face SO-101 Assembly](https://huggingface.co/docs/lerobot/en/so101)
- [Seeed Studio Leader/Follower Assembly](https://wiki.seeedstudio.com/lerobot_so100m_new/#assembly)

Leader arm gear ratios (SO101):

| Joint | Motor | Gear Ratio |
|-------|-------|------------|
| 1 (base) | ST-3215-C044 | 1:191 |
| 2 (shoulder) | ST-3215-C001 | 1:345 |
| 3 (elbow) | ST-3215-C044 | 1:191 |
| 4–6 (wrist, gripper) | ST-3215-C046 | 1:147 |

---

## 5. Calibrate

Calibration ensures leader and follower map the same physical pose to the same joint values.

**Follower:**
```bash
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/so101_follower \
    --robot.id=gi_jane
```

**Leader:**
```bash
lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/so101_leader \
    --teleop.id=gi_joe
```

Use the **same `id`** for teleoperation, recording, and evaluation. Calibration is stored under `~/.cache/huggingface/lerobot/calibration/`.

---

## 6. Teleoperate

Practice the task before recording.

```bash
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/so101_follower \
    --robot.id=gi_jane \
    --teleop.type=so101_leader \
    --teleop.port=/dev/so101_leader \
    --teleop.id=gi_joe
```

---

## 7. Cameras: iPhone and DroidCam

You can use an **iPhone** or Android phone as a camera via [DroidCam](https://www.dev47apps.com/), which turns the phone into a webcam for the PC. This is useful when you don’t have dedicated USB cameras or want multiple views (e.g., front + top) with a phone.

### Setup

1. **Install DroidCam on the phone**
   - [DroidCam Webcam & OBS Camera](https://apps.apple.com/us/app/droidcam-webcam-obs-camera/id1510258102) (iPhone)
   - [DroidCam (Classic)](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam) (Android)

2. **Install the DroidCam PC client** on your computer (Windows, macOS, Linux) from [dev47apps.com](https://www.dev47apps.com/). This installs the virtual webcam driver.

3. **Connect**:
   - **WiFi**: Phone and PC on the same network; DroidCam shows an IP and port (e.g. `192.168.1.x:4747`).
   - **USB**: Enable USB tethering on the phone and connect to the PC.

4. **Start streaming**: Launch DroidCam on the phone, then start the DroidCam client on the PC so the feed is active before running LeRobot.

### Using DroidCam with LeRobot

LeRobot’s OpenCV camera accepts either a device index or a URL.

**Option A — Virtual webcam index**

DroidCam usually shows up as an extra camera (e.g. index `1` or `2`). Find it with:

```bash
lerobot-find-cameras opencv
```

Then use the index in `index_or_path`:

```bash
--robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }"
```

**Option B — HTTP stream (often more stable)**

Use the DroidCam MJPEG URL in `index_or_path`:

- USB: `http://localhost:4747/mjpegfeed`
- WiFi: `http://192.168.x.x:4747/mjpegfeed` (use the IP shown in the DroidCam app)

```bash
--robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }"
```

### Example: Record with DroidCam camera

Teleop has no camera parameter (`teleop.sh`). Cameras are used in `lerobot-record`. To use DroidCam when recording, pass the DroidCam URL in `--robot.cameras`:

```bash
# In record.sh or lerobot-record: use DroidCam URL instead of index 0
--robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }"
```

### Tips

- Free DroidCam: 640×480; Pro: up to 1080p (and 4K for OBS).
- Keep only one app (e.g. LeRobot) using the feed; close other DroidCam users (browsers, video apps).
- For WiFi: keep phone and PC on the same LAN and use a stable connection.
- Camera names (`front`, `side`, etc.) must match between recording and evaluation.

---

## 8. Record a Dataset

For a **local-only workflow** (no Hugging Face Hub): use `--dataset.push_to_hub=false` and `--dataset.root` to save to disk. The `--dataset.repo_id` is just a logical identifier (e.g. `frazier-z/so101`); data is stored under `--dataset.root`, not fetched from or pushed to Hub.

Record episodes:

```bash
lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/so101_follower \
    --robot.id=gi_jane \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/so101_leader \
    --teleop.id=gi_joe \
    --display_data=true \
    --dataset.repo_id=frazier-z/so101 \
    --dataset.num_episodes=50 \
    --dataset.single_task="Grab the wooden rectangular block" \
    --dataset.push_to_hub=false \
    --dataset.episode_time_s=30 \
    --dataset.reset_time_s=30 \
    --dataset.root ~/GitHub/so101/datasets/move_block
```

Tips (from Seeed Studio):

- Record ≥50 episodes (e.g. 10 per location)
- Keep cameras fixed
- Task: grasp object and place in bin
- You should be able to do the task using only the camera images

---

## 9. Train a Policy

Training is done **locally** using `--dataset.root`; the dataset is loaded from disk, not from Hugging Face Hub. Use `--dataset.repo_id` to match the identifier from recording; the actual data path is `--dataset.root`.

### ACT (Action Chunking with Transformers)

```bash
systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/so101 \
    --dataset.root ~/GitHub/so101/datasets/move_block \
    --policy.type=act \
    --output_dir=outputs/train/act_so101_test \
    --job_name=act_so101_test \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=400000
```

The policy adapts to the robot’s motor states, actions, and cameras from the dataset.

### SmolVLA (Vision-Language-Action)

```bash
pip install -e ".[smolvla]"

systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/so101 \
    --dataset.root ~/GitHub/so101/datasets/move_block \
    --policy.type=smolvla \
    --output_dir=outputs/train/smolvla_so101_test \
    --job_name=smolvla_test \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=50000
```

---

## 10. Evaluate

Run the trained policy and record evaluation episodes (e.g. `start-act.sh`):

```bash
lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/so101_follower \
  --robot.id=gi_jane \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/so101_leader \
  --teleop.id=gi_joe \
  --display_data=false \
  --dataset.repo_id=frazier-z/eval_so101 \
  --dataset.root=/home/zackary-frazier/GitHub/so101/eval_dataset \
  --dataset.num_episodes=5 \
  --dataset.single_task="Grab the wooden rectangular block" \
  --dataset.push_to_hub=false \
  --policy.path=~/GitHub/so101/outputs/train/act_so101_test/checkpoints/400000/pretrained_model \
  --policy.device=cuda
```

---

## My Setup and Workflow (POC for UR12e)

This section documents the exact workflow I used for the SO101 POC, following the bash scripts in `~/GitHub/so101`. **The entire pipeline was local**—no Hugging Face Hub, no `${HF_USER}`, no `hf auth`. Datasets were stored and loaded via `--dataset.root`; models were trained and saved locally. This POC confirmed that the LeRobot pipeline worked before moving to the UR12e.

These scripts have been copied into this repo at `scripts/so-101/` for completeness. They were **not run from there**—the POC was run from `~/GitHub/so101`. The copies in `scripts/so-101/` are for reference only.

### Scripts Used

| Script | Purpose |
|--------|---------|
| `record.sh` | Record teleoperated episodes into a local LeRobot dataset |
| `train-act.sh` | Train ACT policy |
| `train-smolvla.sh` | Train SmolVLA (Vision-Language-Action) policy |
| `start-act.sh` | Run ACT inference |
| `start-smolvla.sh` | Run SmolVLA inference |
| `teleop.sh` | Teleoperate without recording |
| `start-camera.sh` | Launch OBS Studio for camera/streaming |

### Workflow

1. **Record 55 episodes** (local dataset only; `--dataset.push_to_hub=false`)

   From `~/GitHub/so101`, run `record.sh` with `--dataset.num_episodes=55` (or edit the script). The script uses `/dev/so101_follower` and `/dev/so101_leader`, which are created by udev rules that map each arm’s serial controller (by serial number) to consistent device names, independent of USB port.

   ```bash
   lerobot-record --robot.type=so101_follower \
       --robot.port=/dev/so101_follower \
       --robot.id=gi_jane \
       --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }" \
       --teleop.type=so101_leader \
       --teleop.port=/dev/so101_leader \
       --teleop.id=gi_joe \
       --display_data=true \
       --dataset.repo_id=frazier-z/so101 \
       --dataset.num_episodes=55 \
       --dataset.single_task="Grab the wooden rectangular block" \
       --dataset.push_to_hub=false \
       --dataset.episode_time_s=30 \
       --dataset.reset_time_s=30 \
       --resume true \
       --dataset.root ~/GitHub/so101/datasets/move_block
   ```

   Data is saved to `~/GitHub/so101/datasets/move_block`.

2. **POC: ACT with 10 episodes**
   Trained an ACT model on 10 videos as a proof-of-concept (subset of data or early recordings).

3. **ACT with 55 episodes**
   Full training using `train-act.sh`:
   ```bash
   ./train-act.sh
   ```
   The script runs:
   ```bash
   systemd-inhibit --what=sleep --why="LeRobot training" \
     lerobot-train \
       --dataset.repo_id=frazier-z/so101 \
       --dataset.root ~/GitHub/so101/datasets/move_block \
       --policy.type=act \
       --output_dir=outputs/train/act_so101_test \
       --job_name=act_so101_test \
       --policy.device=cuda \
       --wandb.enable=false \
       --policy.push_to_hub=false \
       --steps=400000
   ```
   Training took **14 hours** on this machine.

4. **Evaluation**
   The 55-episode ACT policy achieved about **2/5 success rate** (~40%) during evaluation.

5. **SmolVLA with same dataset**
   Trained a SmolVLA policy using `train-smolvla.sh`:
   ```bash
   ./train-smolvla.sh
   ```
   The script runs:
   ```bash
   systemd-inhibit --what=sleep --why="LeRobot training" \
     lerobot-train \
       --dataset.repo_id=frazier-z/so101 \
       --dataset.root ~/GitHub/so101/datasets/move_block \
       --policy.type=smolvla \
       --output_dir=outputs/train/smolvla_so101_test \
       --job_name=smolvla_test \
       --policy.device=cuda \
       --wandb.enable=false \
       --policy.push_to_hub=false \
       --steps=50000
   ```
   It uses `--steps=50000` (slimmed down from ACT's 400k to reduce training time). The resulting VLA policy was **less productive** than the ACT model, likely due to insufficient training steps for the larger VLA architecture.

### Takeaways (for UR12e planning)

- **ACT + 55 episodes**: ~40% success, 14 hours training; validated that ACT works for this class of task.
- **SmolVLA with 50k steps**: Faster training but poorer performance; VLA likely needs more steps or data.
- **Udev rules** were created to map each arm’s serial controller by serial number to stable device names (`/dev/so101_follower`, `/dev/so101_leader`).
- This POC showed the LeRobot pipeline (record, train, evaluate) is viable before scaling to the UR12e.

---

## References

| Resource | URL | Description |
|----------|-----|-------------|
| SO-ARM100 GitHub | https://github.com/TheRobotStudio/SO-ARM100 | BOM, STL, assembly |
| LeRobot il_robots | https://huggingface.co/docs/lerobot/en/il_robots | Imitation learning workflow |
| LeRobot SO-101 | https://huggingface.co/docs/lerobot/en/so101 | SO101 setup and assembly |
| Seeed Studio SoArm | https://wiki.seeedstudio.com/lerobot_so100m_new/ | SO100/SO101 hardware, calibration, training |
