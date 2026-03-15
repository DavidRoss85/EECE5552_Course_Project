# Copyright 2026 EECE5552 Course Project
# Author: abdul rahman
# mohammedabdulr.1@northeastern.edu
print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest, PlanningOptions, Constraints,
    PositionConstraint, OrientationConstraint,
    RobotState, BoundingVolume,
)
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Header


class GoalController(Node):
    """Listens on /goal_pose and sends Cartesian goals to MoveIt."""

    def __init__(self):
        super().__init__('goal_controller')
        self.client = ActionClient(self, MoveGroup, '/move_action')
        self.get_logger().info('Waiting for MoveGroup action server...')
        self.client.wait_for_server()
        self.get_logger().info('MoveGroup ready')
        self.sub = self.create_subscription(
            PoseStamped, '/goal_pose', self.goal_callback, 10
        )
        self.get_logger().info('Listening on /goal_pose')

    def goal_callback(self, msg):
        self.get_logger().info(
            f'Goal received: x={msg.pose.position.x:.3f} '
            f'y={msg.pose.position.y:.3f} z={msg.pose.position.z:.3f}'
        )
        self.send_goal(msg)

    def send_goal(self, pose_stamped):
        goal_msg = MoveGroup.Goal()
        req = MotionPlanRequest()
        req.group_name = 'ur_manipulator'
        req.allowed_planning_time = 15.0
        req.num_planning_attempts = 10
        req.max_velocity_scaling_factor = 0.3
        req.max_acceleration_scaling_factor = 0.2

        start_state = RobotState()
        start_state.is_diff = True
        req.start_state = start_state

        constraint = Constraints()

        pos_con = PositionConstraint()
        pos_con.header = Header()
        pos_con.header.frame_id = 'world'
        pos_con.link_name = 'tool0'
        bv = BoundingVolume()
        sp = SolidPrimitive()
        sp.type = SolidPrimitive.SPHERE
        sp.dimensions = [0.01]
        bv.primitives.append(sp)
        bv.primitive_poses.append(pose_stamped.pose)
        pos_con.constraint_region = bv
        pos_con.weight = 1.0

        ori_con = OrientationConstraint()
        ori_con.header = Header()
        ori_con.header.frame_id = 'world'
        ori_con.link_name = 'tool0'
        ori_con.orientation = pose_stamped.pose.orientation
        ori_con.absolute_x_axis_tolerance = 0.5
        ori_con.absolute_y_axis_tolerance = 0.5
        ori_con.absolute_z_axis_tolerance = 0.5
        ori_con.weight = 1.0

        constraint.position_constraints.append(pos_con)
        constraint.orientation_constraints.append(ori_con)
        req.goal_constraints = [constraint]
        goal_msg.request = req
        goal_msg.planning_options = PlanningOptions()
        goal_msg.planning_options.plan_only = False

        self.get_logger().info('Sending to MoveGroup...')
        future = self.client.send_goal_async(goal_msg)
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error('Goal rejected')
            return
        self.get_logger().info('Goal accepted, executing...')
        handle.get_result_async().add_done_callback(self.result_callback)

    def result_callback(self, future):
        result = future.result().result
        if result.error_code.val == 1:
            self.get_logger().info('Motion SUCCEEDED')
        else:
            self.get_logger().error(f'Motion FAILED: code {result.error_code.val}')


def main():
    rclpy.init()
    node = GoalController()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
