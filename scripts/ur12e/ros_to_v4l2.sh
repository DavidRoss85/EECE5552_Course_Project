#!/bin/bash
# Run a single ROS Image topic -> v4l2 pipeline.
# Usage: ./ros_to_v4l2.sh <topic> <device>
# Example: ./ros_to_v4l2.sh /cameras/top/image_raw /dev/video10

TOPIC="${1:-/cameras/top/image_raw}"
DEVICE="${2:-/dev/video10}"

ros2 run robot_control ros_image_to_raw --topic "$TOPIC" --width 640 --height 480 | \
  ffmpeg -y -loglevel error -f rawvideo -pix_fmt bgr24 -s 640x480 -r 30 \
    -i pipe:0 -f v4l2 -pix_fmt rgb24 -r 15 "$DEVICE"
