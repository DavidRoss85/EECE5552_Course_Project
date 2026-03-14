rm -rf eval_smolvla
lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/so101_follower \
  --robot.id=gi_jane \
  --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: 'MJPG'} }" \
  --dataset.repo_id=frazier-z/eval_so101 \
  --dataset.root=eval_smolvla \
  --dataset.num_episodes=1 \
  --dataset.single_task="Put the wooden block in the basket plz" \
  --policy.device=cuda \
   --policy.path=/home/zackary-frazier/GitHub/so101/outputs/train/smolvla_so101_test/checkpoints/050000/pretrained_model \
  --dataset.push_to_hub=false