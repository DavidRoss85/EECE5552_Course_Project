systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/ur12e_sim_dataset \
    --policy.type=act \
    --output_dir=$HOME/GitHub/EECE5552_Course_Project/outputs/train/act_ur12e_sim \
    --job_name=act_ur12e_sim \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=1000 \
    --dataset.root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_sim_dataset \