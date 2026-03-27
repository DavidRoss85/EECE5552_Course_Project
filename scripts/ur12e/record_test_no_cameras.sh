#!/usr/bin/env bash

lerobot-record \
    --robot.type=ur12e_ros \
    --teleop.type=ros_twist \
    --dataset.repo_id=frazier-z/ur12e_gripper_test \
    --dataset.root="$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gripper_test_no_cameras" \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=1 \
    --dataset.episode_time_s=20 \
    --dataset.reset_time_s=5 \
    --dataset.single_task="gripper capture test (no cameras)" \
    --robot.cameras="{}" \
    --resume=true
