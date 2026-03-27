#!/usr/bin/env bash
set -euo pipefail

DATASET_ROOT="${HOME}/GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_one_video_test"
GAZE_TOPIC="/eye_gaze_xy"

echo "Cleaning previous test dataset at: ${DATASET_ROOT}"
rm -rf "${DATASET_ROOT}"

echo "Publishing initial gaze sample to ${GAZE_TOPIC}"
ros2 topic pub --once "${GAZE_TOPIC}" std_msgs/msg/Float32MultiArray "{data: [0.45, 0.55]}"

echo "Starting background gaze publisher"
ros2 topic pub "${GAZE_TOPIC}" std_msgs/msg/Float32MultiArray "{data: [0.45, 0.55]}" -r 30 >/tmp/ur12e_gaze_pub.log 2>&1 &
GAZE_PUB_PID=$!
cleanup() {
    if kill -0 "${GAZE_PUB_PID}" >/dev/null 2>&1; then
        kill "${GAZE_PUB_PID}" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

echo "Recording 1 episode with one camera video + gaze observations"
lerobot-record \
    --robot.type=ur12e_ros \
    --teleop.type=ros_twist \
    --dataset.repo_id=frazier-z/ur12e_gaze_one_video_test \
    --dataset.root="${DATASET_ROOT}" \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=1 \
    --dataset.episode_time_s=20 \
    --dataset.reset_time_s=5 \
    --dataset.single_task="gaze observation + one video test" \
    --robot.ros2_interface.enable_gaze_input=true \
    --robot.ros2_interface.gaze_topic_name="${GAZE_TOPIC}" \
    --robot.ros2_interface.gaze_default_x=0.45 \
    --robot.ros2_interface.gaze_default_y=0.55 \
    --robot.cameras="{ front: {type: opencv, index_or_path: 'ros:///cameras/front/image_raw', width: 640, height: 480, fps: 30 } }" \
    --resume=true

echo
echo "Recorded dataset stats:"
python - <<'PY'
import json
from pathlib import Path

stats_path = Path.home() / "GitHub/EECE5552_Course_Project/datasets/ur12e_gaze_one_video_test/meta/stats.json"
if not stats_path.exists():
    raise SystemExit(f"stats.json not found at {stats_path}")

stats = json.loads(stats_path.read_text())
print(json.dumps(stats, indent=2))
PY

echo
echo "Video files:"
rg --files "${DATASET_ROOT}/videos" || true
