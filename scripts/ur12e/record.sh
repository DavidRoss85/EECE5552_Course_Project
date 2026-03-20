rm -rf /home/zackary-frazier/GitHub/EECE5552_Course_Project/datasets/ur12e_sim_dataset
lerobot-record \
    --robot.type=ur12e_ros \
    --teleop.type=ros_twist \
    --dataset.repo_id=frazier-z/ur12e \
    --dataset.root=$HOME/GitHub/EECE5552_Course_Project/datasets/ur12e_sim_dataset \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=5 \
    --dataset.episode_time_s=45 \
    --dataset.reset_time_s=20 \
    --dataset.single_task="pick up imaginary block" \
    --robot.cameras="{ top: {type: opencv, index_or_path: 'ros:///cameras/top/image_raw', width: 640, height: 480, fps: 30 }, side: {type: opencv, index_or_path: 'ros:///cameras/side/image_raw', width: 640, height: 480, fps: 30 }, front: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 30 } }" \
    --resume false
