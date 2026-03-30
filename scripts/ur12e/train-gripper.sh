systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/ur12e_gripper_test \
    --policy.type=smolvla \
    --output_dir=outputs/train/smolvla_ur12e_gripper_test \
    --job_name=smolvla_ur12e_gripper_test \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=1000 \
    --dataset.root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gripper_test
    --resume true