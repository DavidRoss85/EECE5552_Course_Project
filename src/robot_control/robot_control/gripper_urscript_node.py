"""Bridges /gripper_position (Float64, 0=closed 1=open) to the UR12e gripper
via a direct TCP socket to port 30002 (URScript secondary interface).

Follows the same pattern as lab4pt9: open a persistent socket to the robot,
send rq_* URScript commands as plain UTF-8 strings whenever the gripper
state changes.

Parameters
----------
robot_ip : str
    IP address of the UR12e (default "10.0.0.134").
robot_port : int
    URScript secondary interface port (default 30002).
gripper_topic : str
    Input topic (default "/gripper_position").
resend_on_connect : bool
    Whether to call resend_robot_program after gripper startup (default True).
resend_robot_program_service : str
    Service used to re-enable External Control
    (default "/io_and_status_controller/resend_robot_program").
"""

import socket

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from std_srvs.srv import Trigger

_OPEN_CMD = "rq_open()\n"
_CLOSE_CMD = "rq_close()\n"


class GripperURScriptNode(Node):

    def __init__(self):
        super().__init__('gripper_urscript_node')

        self.declare_parameter('robot_ip', '10.245.216.50')
        self.declare_parameter('robot_port', 30002)
        self.declare_parameter('gripper_topic', '/gripper_position')
        self.declare_parameter('resend_on_connect', True)
        self.declare_parameter(
            'resend_robot_program_service',
            '/io_and_status_controller/resend_robot_program',
        )

        self._sock: socket.socket | None = None
        self._is_open: bool | None = None   # last sent state; None = unknown

        gripper_topic = self.get_parameter('gripper_topic').get_parameter_value().string_value
        self._sub = self.create_subscription(Float64, gripper_topic, self._gripper_cb, 10)
        self.get_logger().info(f"Subscribed to '{gripper_topic}'.")
        resend_service = (
            self.get_parameter('resend_robot_program_service')
            .get_parameter_value()
            .string_value
        )
        self._resend_client = self.create_client(Trigger, resend_service)

        # Connect after spinning starts so __init__ doesn't block
        self._connect_timer = self.create_timer(0.1, self._deferred_connect)

    def _deferred_connect(self) -> None:
        self._connect_timer.cancel()
        self._connect_socket()

    def _connect_socket(self) -> None:
        ip = self.get_parameter('robot_ip').get_parameter_value().string_value
        port = self.get_parameter('robot_port').get_parameter_value().integer_value
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5.0)
            self._sock.connect((ip, port))
            self._sock.settimeout(None)  # back to blocking for sends
            self.get_logger().info(f"Connected to UR12e at {ip}:{port}")
            # Open the gripper on connection
            self._send(_OPEN_CMD)
            self.get_logger().info("Opened gripper on connection")
            self._log_on_robot("Gripper opened on connection")
            if self.get_parameter('resend_on_connect').get_parameter_value().bool_value:
                self._request_resend_robot_program()
        except Exception as e:
            self.get_logger().error(f"Could not connect to robot: {e}")
            self._sock = None
            return

    def _request_resend_robot_program(self) -> None:
        service_name = (
            self.get_parameter('resend_robot_program_service')
            .get_parameter_value()
            .string_value
        )
        if not self._resend_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn(
                f"Service '{service_name}' not available; could not resend robot program."
            )
            return
        future = self._resend_client.call_async(Trigger.Request())
        future.add_done_callback(self._on_resend_robot_program_done)
        self.get_logger().info(f"Requested '{service_name}' to re-enable External Control.")

    def _on_resend_robot_program_done(self, future) -> None:
        try:
            response = future.result()
        except Exception as e:
            self.get_logger().error(f"resend_robot_program call failed: {e}")
            return

        if response.success:
            self.get_logger().info(f"resend_robot_program succeeded: {response.message}")
        else:
            self.get_logger().warn(f"resend_robot_program rejected: {response.message}")

    def _send(self, cmd: str) -> bool:
        if self._sock is None:
            self.get_logger().warn("Socket not connected; dropping command.")
            return False
        try:
            self._sock.sendall(cmd.encode('utf-8'))
            self.get_logger().debug(f"Sent: {cmd.strip()}")
            return True
        except Exception as e:
            self.get_logger().error(f"Send failed: {e}. Attempting reconnect.")
            self._sock = None
            self._connect_socket()
            return False

    def _gripper_cb(self, msg: Float64) -> None:
        if msg.data == 1.0:
            desired_open = True
        elif msg.data == 0.0:
            desired_open = False
        else:
            self.get_logger().warn(f"Invalid gripper data: {msg.data}")
            return

        if desired_open == self._is_open:
            return  # no state change, don't spam the robot

        if self._send(_OPEN_CMD if desired_open else _CLOSE_CMD):
            self._is_open = desired_open
            label = "opened" if desired_open else "closed"
            self.get_logger().info(f"Gripper {label}")
            self._log_on_robot(f"Gripper {label}")

    def _log_on_robot(self, msg: str) -> None:
        if self._send(f"textmsg(\"{msg}\")\n"):
            self.get_logger().info(f"Logged to robot: {msg}")
        else:
            self.get_logger().warn(f"Failed to log to robot: {msg}")

    def destroy_node(self):
        if self._sock:
            self._sock.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = GripperURScriptNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
