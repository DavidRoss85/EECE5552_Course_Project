systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/so101 \
    --policy.type=smolvla \
    --output_dir=outputs/train/smolvla_so101_test \
    --job_name=smolvla_test \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=50000 \
    --dataset.root ~/GitHub/so101/datasets/move_block