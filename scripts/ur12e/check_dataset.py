import os
from pathlib import Path

from tqdm import tqdm
from lerobot.datasets.lerobot_dataset import LeRobotDataset

PROJECT_ROOT = Path(os.path.abspath(__file__)).parents[2]

dataset = LeRobotDataset(
    "frazier-z/ur12e_gaze_with_gripper",
    root=PROJECT_ROOT / "datasets" / "ur12e_gaze_with_gripper",
)
for frame in tqdm(dataset):
    pass
print("All frames loaded successfully.")