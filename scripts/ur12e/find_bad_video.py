import os
import pandas as pd
from torchcodec.decoders import VideoDecoder

DATASET_ROOT = os.path.expanduser(
    "~/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_with_gripper"
)
CAMERA_KEYS = [
    "observation.images.top",
    "observation.images.side",
    "observation.images.gripper",
]
FPS = 15

bad_episodes = []

for ep_idx in range(51):
    parquet_path = os.path.join(
        DATASET_ROOT, "data", "chunk-000", f"file-{ep_idx:03d}.parquet"
    )
    if not os.path.exists(parquet_path):
        continue

    df = pd.read_parquet(parquet_path)
    max_frame_index = df["frame_index"].max()

    for cam_key in CAMERA_KEYS:
        video_path = os.path.join(
            DATASET_ROOT, "videos", cam_key, "chunk-000", f"file-{ep_idx:03d}.mp4"
        )
        if not os.path.exists(video_path):
            bad_episodes.append((ep_idx, cam_key, "MISSING VIDEO"))
            continue

        decoder = VideoDecoder(video_path)
        num_frames = decoder.metadata.num_frames

        if max_frame_index >= num_frames:
            bad_episodes.append((ep_idx, cam_key,
                f"frame {max_frame_index} requested but video has {num_frames} frames"))

        fps = decoder.metadata.average_fps
        timestamps = df["timestamp"].values
        max_ts_frame = max(round(ts * fps) for ts in timestamps)

        if max_ts_frame >= num_frames:
            bad_episodes.append((ep_idx, cam_key,
                f"timestamp-derived frame {max_ts_frame} but video has {num_frames} frames"))

if bad_episodes:
    print(f"Found {len(bad_episodes)} issues:\n")
    for ep_idx, cam_key, reason in bad_episodes:
        print(f"  Episode {ep_idx:3d} | {cam_key} | {reason}")
else:
    print("All episodes OK.")