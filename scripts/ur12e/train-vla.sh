systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/ur12e_gaze \
    --policy.type=smolvla \
    --output_dir=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_gaze \
    --job_name=smolvla_ur12e_gaze \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=25000 \
    --dataset.root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze