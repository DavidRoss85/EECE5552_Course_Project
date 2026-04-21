#!/usr/bin/env bash
# Example: gaze + multi-camera recording. Usage: bash record_gaze.sh <gaze_x> <gaze_y>
set -euo pipefail
lerobot-record \
    --robot.type=ur12e_ros \
    --teleop.type=ros_twist \
    --dataset.repo_id=frazier-z/ur12e_gaze_with_gripper \
    --dataset.root="$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_with_gripper" \
    --dataset.push_to_hub=false \
    --dataset.fps=15 \
    --dataset.num_episodes=5 \
    --dataset.episode_time_s=60 \
    --dataset.reset_time_s=60 \
    --dataset.single_task="grab target block" \
    --robot.ros2_interface.enable_gaze_input=true \
    --robot.ros2_interface.gaze_topic_name=/vla/coords \
    --robot.ros2_interface.gaze_default_x=$1 \
    --robot.ros2_interface.gaze_default_y=$2 \
    --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 15 }, side: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 15 }, gripper: {type: opencv, index_or_path: /dev/video1, width: 640, height: 480, fps: 15 } }" \
    --resume=true