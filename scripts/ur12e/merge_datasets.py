import os
from pathlib import Path

import torch
from tqdm import tqdm
from lerobot.datasets.lerobot_dataset import LeRobotDataset

PROJECT_ROOT = Path(os.path.abspath(__file__)).parents[2]

SKIP_EPISODES_3CAM = {28}

src_3cam = LeRobotDataset(
    "frazier-z/ur12e_gaze_with_gripper",
    root=PROJECT_ROOT / "datasets" / "ur12e_gaze_with_gripper",
)
src_2cam = LeRobotDataset(
    "frazier-z/ur12e_gaze",
    root=PROJECT_ROOT / "datasets" / "ur12e_gaze",
)

dst = LeRobotDataset.create(
    repo_id="frazier-z/ur12e_combined",
    root=PROJECT_ROOT / "datasets" / "ur12e_combined",
    fps=src_3cam.fps,
    robot_type=src_3cam.meta.robot_type,
    features=src_3cam.features,
)

black_frame = torch.zeros(480, 640, 3)

KEYS_TO_STRIP = {"frame_index", "episode_index", "index", "task_index", "timestamp"}


def clean_frame(frame: dict) -> dict:
    cleaned = {}
    for k, v in frame.items():
        if k in KEYS_TO_STRIP:
            continue
        if isinstance(v, torch.Tensor) and v.ndim == 3 and v.shape[0] == 3:
            v = v.permute(1, 2, 0)
        cleaned[k] = v
    return cleaned


print("Adding 3-camera episodes...")
current_ep = None
for idx in tqdm(range(len(src_3cam))):
    frame = src_3cam[idx]
    ep_idx = frame["episode_index"].item()
    if ep_idx in SKIP_EPISODES_3CAM:
        continue
    if current_ep is not None and ep_idx != current_ep:
        dst.save_episode()
    current_ep = ep_idx
    dst.add_frame(clean_frame(frame))
if current_ep is not None:
    dst.save_episode()

print("Adding 2-camera episodes (with black gripper frame)...")
current_ep = None
for idx in tqdm(range(len(src_2cam))):
    frame = src_2cam[idx]
    ep_idx = frame["episode_index"].item()
    if current_ep is not None and ep_idx != current_ep:
        dst.save_episode()
    current_ep = ep_idx
    cleaned = clean_frame(frame)
    cleaned["observation.images.gripper"] = black_frame
    dst.add_frame(cleaned)
if current_ep is not None:
    dst.save_episode()

# Required: episode metadata is buffered (default 10 rows) and only flushed when full or
# on finalize(). Without this, the last (N % 10) episodes never reach meta/episodes/*.parquet
# and __del__ may fail during shutdown — see LeRobotDataset.finalize() docstring.
dst.finalize()

num_3cam = src_3cam.meta.total_episodes - len(SKIP_EPISODES_3CAM)
num_2cam = src_2cam.meta.total_episodes
print(f"\nDone! Combined dataset: {dst.meta.total_episodes} episodes, {dst.meta.total_frames} frames")
print(f"  Episodes 0-{num_3cam - 1}: 3-camera data ({num_3cam} episodes)")
print(f"  Episodes {num_3cam}-{num_3cam + num_2cam - 1}: 2-camera data with black gripper ({num_2cam} episodes)")

print(f"\nFor 3-cam-only fine-tuning (stage 2), use:")
print(f'  --dataset.episodes="{list(range(num_3cam))}"')
