ROOT="${HOME}/GitHub/EECE5552_Course_Project"
DATASET_DIR="$HOME/GitHub/EECE5552_Course_Project/eval_datasets/eval_ur12e_act_v2_20"
if [ -d "$DATASET_DIR" ]; then
  RESUME=true
else
  RESUME=false
fi

lerobot-record \
  --robot.type=ur12e_ros \
  --robot.id=ur12e \
  --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 15 }, side: {type: opencv, index_or_path: /dev/video6, width: 640, height: 480, fps: 15 }, gripper: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 15 } }" \
  --dataset.repo_id=frazier-z/eval_ur12e_act_v2_20\
  --dataset.root=$HOME/GitHub/EECE5552_Course_Project/eval_datasets/eval_ur12e_act_v2_20 \
  --dataset.num_episodes=1 \
  --dataset.single_task="grab target block" \
  --policy.device=cuda \
  --policy.path=$HOME/GitHub/EECE5552_Course_Project/outputs/train/ur12e-act-v2/checkpoints/005000/pretrained_model \
  --dataset.episode_time_s=90 \
  --dataset.push_to_hub=false \
  --robot.ros2_interface.enable_gaze_input=true \
  --robot.ros2_interface.gaze_topic_name=/vla/coords \
  --robot.ros2_interface.gaze_default_x=$1 \
  --robot.ros2_interface.gaze_default_y=$2 \
  --dataset.fps=15 \
  --teleop.type=ros_twist \
  --resume=$RESUME

