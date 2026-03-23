systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/ur12e \
    --policy.type=smolvla \
    --output_dir=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_test \
    --job_name=smolvla_ur12e_test \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=50000 \
    --dataset.root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_sim_dataset \
    --resume false