rm -rf eval_smolvla
lerobot-record \
  --robot.type=ur12e_ros \
  --robot.id=ur12e \
  --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/top/image_raw', width: 640, height: 480, fps: 30 }, side: {type: opencv, index_or_path: 'ros:///cameras/side/image_raw', width: 640, height: 480, fps: 30 }, front: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 30 } }" \
  --dataset.repo_id=frazier-z/eval_ur12e \
  --dataset.root=eval_smolvla\
  --dataset.num_episodes=1 \
  --dataset.single_task="pick up imaginary block" \
  --policy.device=cuda \
  --policy.path=$HOME/GitHub/EECE5552_Course_Project/outputs/train/smolvla_ur12e_test/checkpoints/050000/pretrained_model \
  --dataset.push_to_hub=false