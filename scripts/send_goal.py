# Copyright 2026 EECE5552 Course Project
# Author: abdul rahman
# mohammedabdulr.1@northeastern.edu
print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

"""
Usage:
    python3 scripts/send_goal.py
    python3 scripts/send_goal.py --x -0.1 --y 0.3 --z 1.3
"""

import argparse
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


def main():
    parser = argparse.ArgumentParser(description='Send pose goal to UR12e')
    parser.add_argument('--x',  type=float, default=-0.1)
    parser.add_argument('--y',  type=float, default=0.3)
    parser.add_argument('--z',  type=float, default=1.3)
    parser.add_argument('--qx', type=float, default=0.0)
    parser.add_argument('--qy', type=float, default=0.0)
    parser.add_argument('--qz', type=float, default=0.0)
    parser.add_argument('--qw', type=float, default=1.0)
    args = parser.parse_args()

    rclpy.init()
    node = Node('goal_sender')
    pub = node.create_publisher(PoseStamped, '/goal_pose', 10)
    time.sleep(1.0)

    msg = PoseStamped()
    msg.header.frame_id = 'world'
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.pose.position.x = args.x
    msg.pose.position.y = args.y
    msg.pose.position.z = args.z
    msg.pose.orientation.x = args.qx
    msg.pose.orientation.y = args.qy
    msg.pose.orientation.z = args.qz
    msg.pose.orientation.w = args.qw

    pub.publish(msg)
    node.get_logger().info(f'Sent goal → x={args.x} y={args.y} z={args.z}')
    time.sleep(0.5)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
