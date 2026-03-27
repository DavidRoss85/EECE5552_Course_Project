#!/usr/bin/env bash

lerobot-record \
    --robot.type=ur12e_ros \
    --teleop.type=ros_twist \
    --dataset.repo_id=frazier-z/ur12e_gaze_test \
    --dataset.root="$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_test" \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=2 \
    --dataset.episode_time_s=20 \
    --dataset.reset_time_s=5 \
    --dataset.single_task="gaze test with one video" \
    --robot.ros2_interface.enable_gaze_input=true \
    --robot.ros2_interface.gaze_topic_name=/eye_gaze_xy \
    --robot.ros2_interface.gaze_default_x=0.0 \
    --robot.ros2_interface.gaze_default_y=0.0 \
    --robot.cameras="{}" \
    --resume=false
