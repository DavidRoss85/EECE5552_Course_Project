#!/usr/bin/env bash
rm -rf "$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_test"
lerobot-record \
    --robot.type=ur12e_ros \
    --teleop.type=ros_twist \
    --dataset.repo_id=frazier-z/ur12e_gaze_test \
    --dataset.root="$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_test" \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=2 \
    --dataset.episode_time_s=45 \
    --dataset.reset_time_s=30 \
    --dataset.single_task="gaze test with one video" \
    --robot.ros2_interface.enable_gaze_input=true \
    --robot.ros2_interface.gaze_topic_name=/vla/coords \
    --robot.ros2_interface.gaze_default_x=0.0 \
    --robot.ros2_interface.gaze_default_y=0.0 \
    --robot.cameras="{ front: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 30 }, side: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 30 } }" \
    --resume=false
