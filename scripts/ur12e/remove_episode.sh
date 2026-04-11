lerobot-edit-dataset \
    --repo_id frazier-z/ur12e_gaze_with_gripper_clean \
    --new_repo_id frazier-z/ur12e_gaze_with_gripper_clean_v3 \
    --operation.type delete_episodes \
    --operation.episode_indices "[54]" \
    --root $HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_with_gripper_clean