"""MoveIt bridge for Robotiq socket gripper control.

This node exposes standard gripper action interfaces so MoveIt-style clients can
command the gripper, while forwarding gripper commands over the Robotiq socket
interface (default port 63352).

Exposed interfaces:
- /gripper_controller/follow_joint_trajectory (control_msgs/action/FollowJointTrajectory)
- /gripper_controller/gripper_cmd (control_msgs/action/GripperCommand)
- /gripper_position (std_msgs/Float64, legacy compatibility)

The gripper joint name defaults to "tool0" to match this project's convention.
"""

from __future__ import annotations

import socket
import time

import rclpy
from control_msgs.action import FollowJointTrajectory, GripperCommand
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node
from std_msgs.msg import Float64
from std_srvs.srv import Trigger

_GRIPPER_OPEN_POS = 0
_GRIPPER_CLOSED_POS = 255


class GripperMoveItBridge(Node):
    def __init__(self) -> None:
        super().__init__("gripper_moveit_bridge")

        self.declare_parameter("robot_ip", "10.245.216.50")
        self.declare_parameter("gripper_port", 63352)
        self.declare_parameter("gripper_joint_name", "tool0")
        self.declare_parameter("gripper_topic", "/gripper_position")
        self.declare_parameter("open_threshold", 0.5)
        self.declare_parameter("activate_gripper_on_start", True)
        self.declare_parameter("recover_external_control", False)
        self.declare_parameter(
            "resend_robot_program_service",
            "/io_and_status_controller/resend_robot_program",
        )
        self.declare_parameter("dashboard_play_service", "/dashboard_client/play")

        self._is_open: bool | None = None
        self._gripper_joint = self.get_parameter("gripper_joint_name").value
        self._open_threshold = float(self.get_parameter("open_threshold").value)
        self._robot_ip = str(self.get_parameter("robot_ip").value)
        self._gripper_port = int(self.get_parameter("gripper_port").value)

        resend_service = self.get_parameter("resend_robot_program_service").value
        dashboard_play_service = self.get_parameter("dashboard_play_service").value
        self._resend_client = self.create_client(Trigger, resend_service)
        self._play_client = self.create_client(Trigger, dashboard_play_service)

        gripper_topic = self.get_parameter("gripper_topic").value
        self._topic_sub = self.create_subscription(
            Float64, gripper_topic, self._gripper_topic_cb, 10
        )
        self.get_logger().info(f"Subscribed to '{gripper_topic}'.")

        self._traj_action = ActionServer(
            self,
            FollowJointTrajectory,
            "/gripper_controller/follow_joint_trajectory",
            goal_callback=self._traj_goal_cb,
            cancel_callback=self._traj_cancel_cb,
            execute_callback=self._traj_execute_cb,
        )
        self._gripper_action = ActionServer(
            self,
            GripperCommand,
            "/gripper_controller/gripper_cmd",
            goal_callback=self._gripper_goal_cb,
            cancel_callback=self._gripper_cancel_cb,
            execute_callback=self._gripper_execute_cb,
        )
        self.get_logger().info(
            "Action servers ready: "
            "/gripper_controller/follow_joint_trajectory, /gripper_controller/gripper_cmd"
        )

        if bool(self.get_parameter("activate_gripper_on_start").value):
            if self._activate_gripper():
                self.get_logger().info(
                    f"Activated gripper over {self._robot_ip}:{self._gripper_port}"
                )
            else:
                self.get_logger().warn(
                    "Failed to activate gripper on start. Open/close may not move "
                    "until gripper is activated."
                )

    def _send_gripper_lines(self, lines: list[str], timeout_s: float = 1.0) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout_s)
                sock.connect((self._robot_ip, self._gripper_port))
                for line in lines:
                    sock.sendall(f"{line}\n".encode("utf-8"))
            return True
        except Exception as exc:
            self.get_logger().error(
                f"Gripper socket command failed ({self._robot_ip}:{self._gripper_port}): {exc}"
            )
            return False

    def _activate_gripper(self) -> bool:
        # Same activation sequence used in direct-script control.
        ok = self._send_gripper_lines(["SET ACT 1"])
        time.sleep(0.1)
        ok = self._send_gripper_lines(["SET MOD 0"]) and ok
        time.sleep(0.1)
        ok = self._send_gripper_lines(["SET GTO 1"]) and ok
        time.sleep(0.1)
        ok = self._send_gripper_lines(["SET SPE 255", "SET FOR 255"]) and ok
        return ok

    def _send_gripper_position(self, position: int) -> bool:
        return self._send_gripper_lines(["SET GTO 1", f"SET POS {position}"], timeout_s=0.5)

    def _command_gripper(self, desired_open: bool, source: str) -> bool:
        if desired_open == self._is_open:
            return True

        position = _GRIPPER_OPEN_POS if desired_open else _GRIPPER_CLOSED_POS
        if not self._send_gripper_position(position):
            return False

        self._is_open = desired_open
        label = "opened" if desired_open else "closed"
        self.get_logger().info(f"Gripper {label} ({source})")

        if bool(self.get_parameter("recover_external_control").value):
            self._recover_external_control()
        return True

    def _recover_external_control(self) -> None:
        resend_service = self.get_parameter("resend_robot_program_service").value
        if self._resend_client.wait_for_service(timeout_sec=0.5):
            future = self._resend_client.call_async(Trigger.Request())
            future.add_done_callback(
                lambda f: self._on_trigger_done(f, resend_service, warn_on_false=False)
            )
        else:
            self.get_logger().warn(f"Service '{resend_service}' unavailable.")

        play_service = self.get_parameter("dashboard_play_service").value
        if self._play_client.wait_for_service(timeout_sec=0.5):
            future = self._play_client.call_async(Trigger.Request())
            future.add_done_callback(
                lambda f: self._on_trigger_done(f, play_service, warn_on_false=True)
            )
        else:
            self.get_logger().warn(f"Service '{play_service}' unavailable.")

    def _on_trigger_done(self, future, name: str, warn_on_false: bool) -> None:
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().warn(f"Service call failed '{name}': {exc}")
            return

        if response.success:
            self.get_logger().debug(f"Service '{name}' succeeded.")
        elif warn_on_false:
            self.get_logger().warn(f"Service '{name}' returned false: {response.message}")

    def _gripper_topic_cb(self, msg: Float64) -> None:
        if msg.data == 1.0:
            desired_open = True
        elif msg.data == 0.0:
            desired_open = False
        else:
            self.get_logger().warn(f"Invalid /gripper_position value: {msg.data}")
            return

        self._command_gripper(desired_open, "topic")

    def _traj_goal_cb(self, goal_request: FollowJointTrajectory.Goal) -> GoalResponse:
        joints = list(goal_request.trajectory.joint_names)
        if joints and self._gripper_joint not in joints:
            self.get_logger().warn(
                f"Rejected gripper trajectory; expected joint '{self._gripper_joint}', got {joints}"
            )
            return GoalResponse.REJECT
        if not goal_request.trajectory.points:
            self.get_logger().warn("Rejected gripper trajectory with no points.")
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _traj_cancel_cb(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _traj_execute_cb(self, goal_handle):
        result = FollowJointTrajectory.Result()
        points = goal_handle.request.trajectory.points
        if not points or not points[-1].positions:
            result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
            result.error_string = "Trajectory has no joint position."
            goal_handle.abort()
            return result

        target = points[-1].positions[0]
        desired_open = target >= self._open_threshold
        if self._command_gripper(desired_open, "trajectory_action"):
            result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
            result.error_string = ""
            goal_handle.succeed()
        else:
            result.error_code = FollowJointTrajectory.Result.PATH_TOLERANCE_VIOLATED
            result.error_string = "Failed to send gripper socket command."
            goal_handle.abort()
        return result

    def _gripper_goal_cb(self, _goal_request: GripperCommand.Goal) -> GoalResponse:
        return GoalResponse.ACCEPT

    def _gripper_cancel_cb(self, _goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _gripper_execute_cb(self, goal_handle):
        result = GripperCommand.Result()
        desired_open = goal_handle.request.command.position >= self._open_threshold
        success = self._command_gripper(desired_open, "gripper_action")

        result.position = 1.0 if desired_open else 0.0
        result.effort = 0.0
        result.stalled = False
        result.reached_goal = success

        if success:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        return result

    def destroy_node(self):
        self._traj_action.destroy()
        self._gripper_action.destroy()
        super().destroy_node()


def main() -> None:
    rclpy.init()
    node = GripperMoveItBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
