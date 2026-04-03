systemd-inhibit --what=sleep --why="LeRobot training" \
  lerobot-train \
    --dataset.repo_id=frazier-z/ur12e_gaze_with_gripper \
    --policy.type=smolvla \
    --output_dir=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_gaze_with_gripper \
    --job_name=smolvla_ur12e_gaze_with_gripper \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=25000 \
    --dataset.root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_with_gripper \
    --dataset.episodes='[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50]'