systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/ur12e_combined \
    --policy.path=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_gaze_with_gripper_v2/checkpoints/030000/pretrained_model \
    --output_dir=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_combined_2cam \
    --job_name=smolvla_ur12e_combined \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=10000 \
    --dataset.root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_combined