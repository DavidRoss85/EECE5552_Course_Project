#!/usr/bin/env python3
"""
VLA Inference Node
------------------
Acts as the bridge between the orchestrator and LeRobot.

Receives a command JSON on /vla/command, triggers LeRobot inference
via the configured method, and publishes status updates on /vla/status.

Three inference methods (set via ROS2 param 'inference_method'):

  SUBPROCESS          — spawns lerobot-record/eval as a child process.
  POLICY_SERVER_RELAY — runs PolicyServer + a relay RobotClient that
                        captures action vectors and republishes them
                        to /vla/action_output for a downstream controller.
  POLICY_SERVER_DIRECT— runs PolicyServer + a standard RobotClient that
                        talks directly to the UR hardware.

Status messages published to /vla/status:
  "READY"   — node is up and waiting for a command
  "RUNNING" — inference is active
  "DONE"    — episode finished successfully
  "ERROR"   — something went wrong (check logs)
"""

import json
import subprocess
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray

from vla_inference.config.vla_inference_config import (
    STD_VLA_CFG,
    InferenceMethod,
    VlaInferenceConfig,
)


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

class VlaStatus:
    READY   = "READY"
    RUNNING = "RUNNING"
    DONE    = "DONE"
    ERROR   = "ERROR"


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class VlaInferenceNode(Node):

    def __init__(self):
        super().__init__("vla_inference_node")
        self._cfg = STD_VLA_CFG

        # ── Declare / read ROS2 parameters ──────────────────────────────────
        # Every field in VlaInferenceConfig can be overridden from a launch
        # file or the command line.  We declare them all here so they show up
        # in `ros2 param list`.

        self.declare_parameter("inference_method",      self._cfg.inference_method)
        self.declare_parameter("policy_path",           self._cfg.policy_path)
        self.declare_parameter("policy_device",         self._cfg.policy_device)
        self.declare_parameter("lerobot_cmd",           self._cfg.lerobot_cmd)
        self.declare_parameter("robot_type",            self._cfg.robot_type)
        self.declare_parameter("robot_id",              self._cfg.robot_id)
        self.declare_parameter("camera_cfg",            self._cfg.camera_cfg)
        self.declare_parameter("dataset_repo_id",       self._cfg.dataset_repo_id)
        self.declare_parameter("dataset_root",          self._cfg.dataset_root)
        self.declare_parameter("dataset_fps",           self._cfg.dataset_fps)
        self.declare_parameter("dataset_num_episodes",  self._cfg.dataset_num_episodes)
        self.declare_parameter("push_to_hub",           self._cfg.push_to_hub)
        self.declare_parameter("enable_gaze_input",     self._cfg.enable_gaze_input)
        self.declare_parameter("policy_server_host",    self._cfg.policy_server_host)
        self.declare_parameter("policy_server_port",    self._cfg.policy_server_port)
        self.declare_parameter("actions_per_chunk",     self._cfg.actions_per_chunk)
        self.declare_parameter("chunk_size_threshold",  self._cfg.chunk_size_threshold)
        self.declare_parameter("episode_time_s",        self._cfg.episode_time_s)

        self._method = self.get_parameter("inference_method").value
        self.get_logger().info(f"Inference method: {self._method}")

        # ── Publishers ───────────────────────────────────────────────────────
        self._status_pub = self.create_publisher(
            String, self._cfg.topic_status_out, self._cfg.max_messages)
        self._action_pub = self.create_publisher(
            Float32MultiArray, self._cfg.topic_action_out, self._cfg.max_messages)

        # ── Subscribers ──────────────────────────────────────────────────────
        self.create_subscription(
            String, self._cfg.topic_command_in,
            self._on_command, self._cfg.max_messages)

        # ── Internal state ───────────────────────────────────────────────────
        self._busy = False              # guard against overlapping episodes
        self._active_proc = None        # subprocess.Popen handle (method 1)
        self._inference_thread = None   # thread running the episode

        self._publish_status(VlaStatus.READY)
        self.get_logger().info("VLA Inference Node ready.")

    # ── Command callback ─────────────────────────────────────────────────────

    def _on_command(self, msg: String):
        if self._busy:
            self.get_logger().warn(
                "Received command while inference is running — ignoring.")
            return

        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Invalid command JSON: {e}")
            self._publish_status(VlaStatus.ERROR)
            return

        self.get_logger().info(f"Command received: {data}")

        # Pull gaze coordinates out of the command payload.
        # The orchestrator is expected to embed them here so this node is
        # self-contained and doesn't need to subscribe to the gaze topic
        # independently.  They are also published to /vla/coords so that
        # the lerobot ROS2 interface can consume them from that topic.
        target = data.get("target", {})
        gaze_x = float(target.get("x", 0.0))
        gaze_y = float(target.get("y", 0.0))
        task   = data.get("command", "grab target block")

        self._busy = True
        self._publish_status(VlaStatus.RUNNING)

        # Dispatch to the appropriate method on a background thread so the
        # ROS2 spin loop is never blocked.
        self._inference_thread = threading.Thread(
            target=self._run_episode,
            args=(task, gaze_x, gaze_y),
            daemon=True,
        )
        self._inference_thread.start()

    # ── Dispatcher ───────────────────────────────────────────────────────────

    def _run_episode(self, task: str, gaze_x: float, gaze_y: float):
        try:
            if self._method == InferenceMethod.SUBPROCESS:
                self._run_subprocess(task, gaze_x, gaze_y)

            elif self._method == InferenceMethod.POLICY_SERVER_RELAY:
                self._run_policy_server_relay(task, gaze_x, gaze_y)

            elif self._method == InferenceMethod.POLICY_SERVER_DIRECT:
                self._run_policy_server_direct(task, gaze_x, gaze_y)

            else:
                self.get_logger().error(
                    f"Unknown inference method: {self._method}")
                self._publish_status(VlaStatus.ERROR)
                return

            self._publish_status(VlaStatus.DONE)

        except Exception as e:
            self.get_logger().error(f"Inference episode failed: {e}")
            self._publish_status(VlaStatus.ERROR)

        finally:
            self._busy = False

    # =========================================================================
    # Method 1 — Subprocess
    # =========================================================================

    def _run_subprocess(self, task: str, gaze_x: float, gaze_y: float):
        """
        Builds the lerobot-record (or lerobot-eval) CLI command and runs it
        as a child process.  Blocks until the process exits.

        This mirrors your teammate's manual eval command exactly, but with
        gaze_x / gaze_y injected dynamically from the orchestrator command.
        """
        cmd = self.get_parameter("lerobot_cmd").value
        policy_path    = self.get_parameter("policy_path").value
        policy_device  = self.get_parameter("policy_device").value
        robot_type     = self.get_parameter("robot_type").value
        robot_id       = self.get_parameter("robot_id").value
        camera_cfg     = self.get_parameter("camera_cfg").value
        repo_id        = self.get_parameter("dataset_repo_id").value
        dataset_root   = self.get_parameter("dataset_root").value
        fps            = self.get_parameter("dataset_fps").value
        num_episodes   = self.get_parameter("dataset_num_episodes").value
        push_to_hub    = str(self.get_parameter("push_to_hub").value).lower()
        enable_gaze    = self.get_parameter("enable_gaze_input").value
        single_task    = task

        args = [
            cmd,
            f"--robot.type={robot_type}",
            f"--robot.id={robot_id}",
            f"--robot.cameras={camera_cfg}",
            f"--dataset.repo_id={repo_id}",
            f"--dataset.root={dataset_root}",
            f"--dataset.num_episodes={num_episodes}",
            f"--dataset.single_task={single_task}",
            f"--policy.device={policy_device}",
            f"--policy.path={policy_path}",
            f"--dataset.push_to_hub={push_to_hub}",
            f"--dataset.fps={fps}",
        ]

        if enable_gaze:
            args += [
                f"--robot.ros2_interface.enable_gaze_input=true",
                f"--robot.ros2_interface.gaze_topic_name={self._cfg.topic_gaze_coords}",
                f"--robot.ros2_interface.gaze_default_x={gaze_x}",
                f"--robot.ros2_interface.gaze_default_y={gaze_y}",
            ]

        self.get_logger().info(f"Launching subprocess: {' '.join(args)}")

        self._active_proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Stream stdout to the ROS logger so it appears in ros2 launch output
        for line in self._active_proc.stdout:
            self.get_logger().info(f"[lerobot] {line.rstrip()}")

        self._active_proc.wait()
        rc = self._active_proc.returncode
        self._active_proc = None

        if rc != 0:
            raise RuntimeError(
                f"lerobot subprocess exited with return code {rc}")

        self.get_logger().info("Subprocess episode complete.")

    # =========================================================================
    # Method 2 — PolicyServer + relay RobotClient
    # =========================================================================

    def _run_policy_server_relay(self, task: str, gaze_x: float, gaze_y: float):
        """
        Starts a PolicyServer in a background thread, then connects a
        custom RobotClient that intercepts action vectors and republishes
        them to /vla/action_output instead of sending them to hardware.

        A downstream controller node (to be built) subscribes to
        /vla/action_output and applies the joint commands to the UR arm.

        TODO: Requires lerobot async inference API integration.
              Implement once the PolicyServer / RobotClient Python API
              is confirmed importable in this environment.
        """
        self.get_logger().warn(
            "POLICY_SERVER_RELAY is not yet implemented. "
            "Falling back to SUBPROCESS.")
        self._run_subprocess(task, gaze_x, gaze_y)

        # --- Implementation outline (fill in when API is confirmed) ----------
        # from lerobot.async_inference.policy_server import PolicyServer
        # from lerobot.async_inference.robot_client  import RobotClient
        #
        # host = self.get_parameter("policy_server_host").value
        # port = self.get_parameter("policy_server_port").value
        #
        # server = PolicyServer(host=host, port=port)
        # server_thread = threading.Thread(target=server.serve, daemon=True)
        # server_thread.start()
        #
        # # Custom RobotClient subclass that overrides the action execution
        # # step to publish to /vla/action_output instead of the hardware.
        # client = RelayRobotClient(
        #     server_address=f"{host}:{port}",
        #     action_callback=self._relay_action_callback,
        #     task=task,
        #     gaze_x=gaze_x,
        #     gaze_y=gaze_y,
        #     episode_time_s=self.get_parameter("episode_time_s").value,
        # )
        # client.run()           # blocks until episode_time_s elapses
        # server.shutdown()
        # ---------------------------------------------------------------------

    def _relay_action_callback(self, action_vector):
        """
        Called by the relay RobotClient each time the PolicyServer returns
        an action chunk.  Publishes the vector to /vla/action_output.
        """
        msg = Float32MultiArray()
        msg.data = [float(v) for v in action_vector]
        self._action_pub.publish(msg)

    # =========================================================================
    # Method 3 — PolicyServer + direct RobotClient (talks to hardware)
    # =========================================================================

    def _run_policy_server_direct(self, task: str, gaze_x: float, gaze_y: float):
        """
        Starts a PolicyServer and a standard RobotClient configured to
        talk directly to the UR hardware (same as the CLI, but from Python).
        Publishes DONE when the episode ends.

        TODO: Requires lerobot async inference API integration.
              Implement once the PolicyServer / RobotClient Python API
              is confirmed importable in this environment.
        """
        self.get_logger().warn(
            "POLICY_SERVER_DIRECT is not yet implemented. "
            "Falling back to SUBPROCESS.")
        self._run_subprocess(task, gaze_x, gaze_y)

        # --- Implementation outline ------------------------------------------
        # from lerobot.async_inference.policy_server import PolicyServer
        # from lerobot.async_inference.robot_client  import RobotClient
        #
        # host = self.get_parameter("policy_server_host").value
        # port = self.get_parameter("policy_server_port").value
        #
        # server = PolicyServer(host=host, port=port)
        # server_thread = threading.Thread(target=server.serve, daemon=True)
        # server_thread.start()
        #
        # client = RobotClient(
        #     server_address=f"{host}:{port}",
        #     robot_type=self.get_parameter("robot_type").value,
        #     robot_id=self.get_parameter("robot_id").value,
        #     task=task,
        #     policy_type="smolvla",
        #     pretrained_name_or_path=self.get_parameter("policy_path").value,
        #     policy_device=self.get_parameter("policy_device").value,
        #     actions_per_chunk=self.get_parameter("actions_per_chunk").value,
        #     chunk_size_threshold=self.get_parameter("chunk_size_threshold").value,
        #     episode_time_s=self.get_parameter("episode_time_s").value,
        # )
        # client.run()   # blocks until done
        # server.shutdown()
        # ---------------------------------------------------------------------

    # =========================================================================
    # Helpers
    # =========================================================================

    def _publish_status(self, status: str):
        msg = String()
        msg.data = status
        self._status_pub.publish(msg)
        self.get_logger().info(f"VLA status → {status}")

    def destroy_node(self):
        # Kill any running subprocess cleanly on shutdown
        if self._active_proc and self._active_proc.poll() is None:
            self.get_logger().warn("Terminating active lerobot subprocess...")
            self._active_proc.terminate()
            try:
                self._active_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._active_proc.kill()
        super().destroy_node()


# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = VlaInferenceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()