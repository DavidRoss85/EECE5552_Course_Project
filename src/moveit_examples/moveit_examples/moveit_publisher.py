import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, PlanningOptions
from moveit_msgs.msg import Constraints, JointConstraint, RobotState
from sensor_msgs.msg import JointState


class MoveGroupClient(Node):

    def __init__(self):
        super().__init__("moveit_client")

        self.client = ActionClient(self, MoveGroup, "/move_action")

        self.get_logger().info("Waiting for MoveGroup action server...")
        self.client.wait_for_server()

        self.send_goal()

    def send_goal(self):

        goal_msg = MoveGroup.Goal()

        req = MotionPlanRequest()
        req.group_name = "ur_manipulator"

        # Allow planner time
        req.allowed_planning_time = 5.0

        # Use current robot state from /joint_states
        start_state = RobotState()
        start_state.is_diff = True
        req.start_state = start_state

        # ---- Goal constraint ----
        constraint = Constraints()

        joint_goal = JointConstraint()
        joint_goal.joint_name = "shoulder_pan_joint"
        joint_goal.position = 0.0
        joint_goal.tolerance_above = 0.1
        joint_goal.tolerance_below = 0.1
        joint_goal.weight = 1.0

        constraint.joint_constraints.append(joint_goal)

        req.goal_constraints = [constraint]

        goal_msg.request = req
        goal_msg.planning_options = PlanningOptions()

        self.get_logger().info("Sending planning request...")

        self.client.send_goal_async(goal_msg)


def main():
    rclpy.init()

    node = MoveGroupClient()

    rclpy.spin(node)


if __name__ == "__main__":
    main()