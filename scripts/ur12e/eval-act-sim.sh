#!/usr/bin/env bash
# Run ACT policy trained on ur12e_sim_dataset (act_ur12e_sim) against the live sim stack.
# Prerequisites: ros2 launch launch/sim.launch.py (cameras on /cameras/{top,side,front}/image_raw)

ROOT="${HOME}/GitHub/EECE5552_Course_Project"
POLICY_DIR="${ROOT}/outputs/train/act_ur12e_sim/checkpoints/001000/pretrained_model"
DATASET_DIR="${ROOT}/eval_datasets/eval_act_ur12e_sim"

if [ -d "$DATASET_DIR" ]; then
  RESUME=true
else
  RESUME=false
fi

lerobot-record \
  --robot.type=ur12e_ros \
  --robot.id=ur12e \
  --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/top/image_raw', width: 640, height: 480, fps: 30 }, side: {type: opencv, index_or_path: 'ros:///cameras/side/image_raw', width: 640, height: 480, fps: 30 }, front: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 30 } }" \
  --dataset.repo_id=frazier-z/eval_act_ur12e_sim \
  --dataset.root="$DATASET_DIR" \
  --dataset.num_episodes=1 \
  --dataset.single_task="grab target block" \
  --policy.device=cuda \
  --policy.path="$POLICY_DIR" \
  --dataset.episode_time_s=120 \
  --dataset.push_to_hub=false \
  --dataset.fps=30 \
  --resume="$RESUME" \
  --robot.ros2_interface.gripper_joint_name=""