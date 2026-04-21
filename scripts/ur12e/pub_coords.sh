#!/usr/bin/env bash
# Launches perception:vla_detector — captures the front camera (ROS topic),
# runs HSV color detection, and publishes coordinates for the current LeRobot /
# gaze pipeline on /vla/coords (std_msgs/Float32MultiArray [cx, cy] of the
# largest blob among the configured colors). Also publishes /vla/target (color
# name) and /vla/preview (annotated sensor_msgs/Image).
#
# Same topic record_gaze.sh and start-act.sh use via:
#   --robot.ros2_interface.gaze_topic_name=/vla/coords
#
# Target which cube(s) to prefer by color (bench red / blue cubes):
#   bash scripts/ur12e/pub_coords.sh        # default: red only
#   bash scripts/ur12e/pub_coords.sh blue   # blue cube only
#   bash scripts/ur12e/pub_coords.sh red    # explicit red
# Yellow is supported by the node if your scene has a yellow block.
#
# Requires: source install/setup.bash; camera publishing /cameras/front/image_raw.
set -euo pipefail
COLOR="${1:-red}"
ros2 run perception vla_detector --ros-args \
  -p camera_source:=topic \
  -p camera_topic:=/cameras/front/image_raw \
  -p "colors:=[\"${COLOR}\"]" \
  -p display:=true
