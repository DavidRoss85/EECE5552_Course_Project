rm -rf eval_dataset
lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/so101_follower \
  --robot.id=gi_jane \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/so101_leader \
  --teleop.id=gi_joe \
  --display_data=false \
  --dataset.repo_id=frazier-z/eval_so101 \
  --dataset.root=/home/zackary-frazier/GitHub/so101/eval_dataset \
  --dataset.num_episodes=5 \
  --dataset.single_task="Grab the wooden rectangular block" \
  --dataset.push_to_hub=false \
  --policy.path=/home/zackary-frazier/GitHub/so101/outputs/train/act_so101_test/checkpoints/400000/pretrained_model \
  --policy.device=cuda