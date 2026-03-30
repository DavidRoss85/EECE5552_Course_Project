rm -rf eval_ur12e_gripper
lerobot-record \
  --robot.type=ur12e_ros \
  --robot.id=ur12e \
  --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 15 }, side: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 15 } }" \
  --dataset.repo_id=frazier-z/eval_ur12e_gripper \
  --dataset.root=eval_ur12e_gripper \
  --dataset.num_episodes=1 \
  --dataset.single_task="move gripper" \
  --policy.device=cuda \
  --policy.path=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_gripper_test/checkpoints/001000/pretrained_model \
  --dataset.push_to_hub=false \
  --robot.ros2_interface.enable_gaze_input=true \
  --robot.ros2_interface.gaze_topic_name=/vla/coords \
  --robot.ros2_interface.gaze_default_x=$1 \
  --robot.ros2_interface.gaze_default_y=$2 \
  --dataset.fps=15
