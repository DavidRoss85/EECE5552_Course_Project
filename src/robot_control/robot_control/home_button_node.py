"""Node that sends the arm to home pose when B button is pressed on the joystick.

A button re-enables MoveIt Servo (activates forward_position_controller and unpauses servo_node).
"""

from sensor_msgs.msg import Joy
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import SwitchController
from std_srvs.srv import SetBool
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

HOME_JOINTS = [0.0, -1.5707, 1.5707, -1.5707, -1.5707, 0.0]
JOINT_NAMES = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]
A_BUTTON_IDX = 0
B_BUTTON_IDX = 1


class HomeButtonNode(Node):
    """Subscribes to /joy and sends arm to home pose on B button press."""

    def __init__(self):
        super().__init__("home_button_node")
        self.joy_sub = self.create_subscription(Joy, "/joy", self._joy_cb, 10)
        self.home_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/scaled_joint_trajectory_controller/follow_joint_trajectory",
        )
        self.switch_cli = self.create_client(
            SwitchController,
            "/controller_manager/switch_controller",
        )
        self.servo_pause_cli = self.create_client(
            SetBool,
            "/servo_node/pause_servo",
        )
        self._a_prev = False
        self._b_prev = False
        self._home_in_progress = False

    def _joy_cb(self, msg):
        if self._home_in_progress:
            return

        if len(msg.buttons) > A_BUTTON_IDX:
            a_pressed = bool(msg.buttons[A_BUTTON_IDX])
            if a_pressed and not self._a_prev:
                self._reset_servo()
            self._a_prev = a_pressed

        if len(msg.buttons) > B_BUTTON_IDX:
            b_pressed = bool(msg.buttons[B_BUTTON_IDX])
            if b_pressed and not self._b_prev:
                self._send_home()
            self._b_prev = b_pressed

    def _reset_servo(self):
        """Activate forward_position_controller and unpause servo_node."""
        self.get_logger().info("A pressed: re-enabling MoveIt Servo...")
        if not self.switch_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Controller manager not available")
            return
        req = SwitchController.Request()
        req.activate_controllers = ["forward_position_controller"]
        req.deactivate_controllers = []
        req.strictness = 1  # BEST_EFFORT
        self.switch_cli.call_async(req).add_done_callback(self._on_servo_controller_ready)

    def _on_servo_controller_ready(self, future):
        try:
            future.result()
        except Exception as e:
            self.get_logger().error(f"Controller switch failed: {e}")
        if not self.servo_pause_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Servo pause service not available")
            return
        unpause = SetBool.Request(data=False)  # False = unpaused / running
        self.servo_pause_cli.call_async(unpause).add_done_callback(
            lambda f: self.get_logger().info("MoveIt Servo re-enabled.")
        )

    def _send_home(self):
        if not self.switch_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Controller manager not available")
            return
        self._home_in_progress = True
        self.get_logger().info("B pressed: switching to trajectory controller...")
        req = SwitchController.Request()
        req.activate_controllers = ["scaled_joint_trajectory_controller"]
        req.deactivate_controllers = ["forward_position_controller"]
        req.strictness = 1  # BEST_EFFORT
        self.switch_cli.call_async(req).add_done_callback(self._on_switch_to_traj)

    def _on_switch_to_traj(self, future):
        try:
            result = future.result()
            if not result.ok:
                self.get_logger().error("Switch to trajectory controller failed")
                self._home_in_progress = False
                return
        except Exception as e:
            self.get_logger().error(f"Switch failed: {e}")
            self._home_in_progress = False
            return
        self.get_logger().info("Sending home trajectory...")
        self._send_home_goal()

    def _send_home_goal(self):
        if not self.home_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn("Trajectory controller action not available")
            self._switch_back_to_servo()
            return
        traj = JointTrajectory()
        traj.joint_names = JOINT_NAMES
        pt = JointTrajectoryPoint()
        pt.positions = HOME_JOINTS
        pt.time_from_start = Duration(sec=3, nanosec=0)
        traj.points = [pt]
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        future = self.home_client.send_goal_async(goal)
        future.add_done_callback(self._on_goal_sent)

    def _on_goal_sent(self, future):
        try:
            handle = future.result()
            if not handle.accepted:
                self.get_logger().error("Home goal rejected")
                self._switch_back_to_servo()
                return
            result_future = handle.get_result_async()
            result_future.add_done_callback(self._on_home_done)
        except Exception as e:
            self.get_logger().error(f"Send goal failed: {e}")
            self._switch_back_to_servo()

    def _on_home_done(self, future):
        self._switch_back_to_servo()

    def _switch_back_to_servo(self):
        req = SwitchController.Request()
        req.activate_controllers = ["forward_position_controller"]
        req.deactivate_controllers = ["scaled_joint_trajectory_controller"]
        req.strictness = 1
        future = self.switch_cli.call_async(req)
        future.add_done_callback(self._on_switch_back_done)

    def _on_switch_back_done(self, future):
        self._home_in_progress = False
        self.get_logger().info("Returned to Servo control")


def main():
    rclpy.init()
    node = HomeButtonNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
