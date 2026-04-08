#!/usr/bin/env python3
"""
Orchestrator Node
-----------------
The central coordinator that manages the full robot task pipeline:

  Intent Selection → VLA Inference → MoveIt Handoff → Homing → Ready

State machine:
  IDLE      — waiting for intent from intent_selection
  INFERENCE — VLA is running, arm is moving under LeRobot control
  HANDOFF   — VLA is done, moving to preset poses via MoveIt
  HOMING    — returning arm to home position
  ERROR     — something went wrong

Command types from intent_selection:
  "general"  — no arm movement, just execute some preset action
  "targeted" — has gaze coordinates, goes through full inference pipeline

The orchestrator owns coordination but does NOT own hardware directly.
It delegates arm control to VLA (during INFERENCE) and MoveIt (during HANDOFF/HOMING).
"""

import json
import time
from enum import Enum
from typing import Optional, Dict, Any

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float64
from geometry_msgs.msg import PoseStamped
from controller_manager_msgs.srv import SwitchController

from system_coordinator.config.ros_presets import STANDARD_ROS_CONFIG as ROS_CFG
from system_coordinator.config.coordinator_config import STD_COORDINATOR_CFG, Pose, Position, Orientation


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class OrchestratorState(str, Enum):
    IDLE        = "IDLE"
    INFERENCE   = "INFERENCE"
    HANDOFF     = "HANDOFF"
    HOMING      = "HOMING" 
    ERROR       = "ERROR"


class CommandType(str, Enum):
    GENERAL     = "general"
    TARGETED    = "targeted"


class VlaStatus(str, Enum):
    READY       = "READY"
    RUNNING     = "RUNNING"
    DONE        = "DONE"
    ERROR       = "ERROR"


# ---------------------------------------------------------------------------
# Orchestrator Node
# ---------------------------------------------------------------------------

class OrchestratorNode(Node):

    def __init__(self):
        super().__init__("orchestrator_node")

        # ── Configuration ────────────────────────────────────────────────────
        # Load defaults from coordinator config, but allow ROS2 param overrides
        cfg = STD_COORDINATOR_CFG
        
        self.declare_parameter("auto_handoff", cfg.auto_handoff)
        self.declare_parameter("handoff_timeout_s", cfg.handoff_timeout_s)
        self.declare_parameter("home_timeout_s", cfg.home_timeout_s)
        self.declare_parameter("gripper_open_pos", cfg.gripper_open_pos)
        self.declare_parameter("gripper_closed_pos", cfg.gripper_closed_pos)
        
        self._auto_handoff = self.get_parameter("auto_handoff").value
        self._handoff_timeout = self.get_parameter("handoff_timeout_s").value
        self._home_timeout = self.get_parameter("home_timeout_s").value
        self._gripper_open = self.get_parameter("gripper_open_pos").value
        self._gripper_closed = self.get_parameter("gripper_closed_pos").value
        
        # Store config for pose access
        self._cfg = cfg

        # ── State ────────────────────────────────────────────────────────────
        self._state = OrchestratorState.IDLE
        self._current_command: Optional[Dict[str, Any]] = None
        self._state_start_time = time.time()

        # ── Publishers ───────────────────────────────────────────────────────
        self._state_pub = self.create_publisher(
            String, ROS_CFG.topic_orchestrator_state, ROS_CFG.max_messages)
        self._vla_command_pub = self.create_publisher(
            String, ROS_CFG.topic_vla_input, ROS_CFG.max_messages)
        self._gaze_coords_pub = self.create_publisher(
            Float64, ROS_CFG.topic_vla_gaze_coords, ROS_CFG.max_messages)  # For debugging/relay
        self._gripper_pub = self.create_publisher(
            Float64, ROS_CFG.topic_gripper_position, ROS_CFG.max_messages)
        self._goal_pose_pub = self.create_publisher(
            PoseStamped, ROS_CFG.topic_goal_pose, ROS_CFG.max_messages)

        # ── Subscribers ──────────────────────────────────────────────────────
        self.create_subscription(
            String, ROS_CFG.topic_intention_output, 
            self._on_intention, ROS_CFG.max_messages)
        self.create_subscription(
            String, ROS_CFG.topic_vla_status,
            self._on_vla_status, ROS_CFG.max_messages)

        # ── Service clients ──────────────────────────────────────────────────
        # Used to switch between controllers when handing off to/from VLA
        self._controller_switch_client = self.create_client(
            SwitchController, "/controller_manager/switch_controller")

        # ── State machine timer ──────────────────────────────────────────────
        # Polls the state machine every 100ms for timeouts and transitions
        self.create_timer(0.1, self._state_machine_tick)

        self._publish_state()
        self.get_logger().info("Orchestrator ready — waiting for intent selection.")

    # ── Intent Selection Input ───────────────────────────────────────────────

    def _on_intention(self, msg: String):
        """
        Receives a JSON command from the intent_selection GUI.
        Expected format:
        {
            "type": "gaze_command",
            "command": "pick up the red block",
            "target": {"x": 320, "y": 240, "name": "red", "confidence": 0.95},
            "original_data": {...},
            "timestamp": 1234567890
        }
        """
        if self._state != OrchestratorState.IDLE:
            self.get_logger().warn(
                f"Received intent while in {self._state} state — ignoring.")
            return

        try:
            data = json.loads(msg.data)
            self.get_logger().info(f"Intent received: {data}")
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Invalid intent JSON: {e}")
            self._transition_to(OrchestratorState.ERROR)
            return

        self._current_command = data
        
        # Determine command type based on the presence of target coordinates
        target = data.get("target", {})
        has_coordinates = "x" in target and "y" in target
        
        if has_coordinates:
            self._handle_targeted_command(data)
        else:
            self._handle_general_command(data)

    #===========================================================
    # COMMAND HANDLERS, HARD BAKED IN FOR NOW:
    #===========================================================
    def _handle_general_command(self, data: Dict[str, Any]):
        """
        Handle commands that don't require arm movement or coordinates.
        Examples: "open gripper", "close gripper", "go home", etc.
        """
        command = data.get("command", "").lower()
        self.get_logger().info(f"Executing general command: {command}")

        if "open" in command and "gripper" in command:
            self._open_gripper()
        elif "close" in command and "gripper" in command:
            self._close_gripper()
        elif "home" in command:
            self._transition_to(OrchestratorState.HOMING)
            return
        else:
            self.get_logger().warn(f"Unknown general command: {command}")
            self._transition_to(OrchestratorState.ERROR)
            return

        # General commands complete immediately
        self.get_logger().info("General command completed.")
        # Stay in IDLE state

    def _handle_targeted_command(self, data: Dict[str, Any]):
        """
        Handle commands with gaze coordinates that require VLA inference.
        """
        command = data.get("command", "grab target block")
        target = data.get("target", {})
        
        # Validate we have the required coordinate data
        if "x" not in target or "y" not in target:
            self.get_logger().error("Targeted command missing x,y coordinates")
            self._transition_to(OrchestratorState.ERROR)
            return

        # Prepare the VLA command
        vla_command = {
            "type": "gaze_command",
            "command": command,
            "target": target,
            "original_data": data,
            "timestamp": int(time.time())
        }

        # Send to VLA inference node
        vla_msg = String()
        vla_msg.data = json.dumps(vla_command)
        self._vla_command_pub.publish(vla_msg)
        
        # Also publish gaze coords to the shared topic for debugging
        gaze_x = float(target["x"])
        gaze_y = float(target["y"])
        self.get_logger().info(f"Sending VLA command: {command} at ({gaze_x}, {gaze_y})")
        
        # Transition to inference state
        self._transition_to(OrchestratorState.INFERENCE)
    #===========================================================

    # ── VLA Status Monitoring ────────────────────────────────────────────────

    def _on_vla_status(self, msg: String):
        """Monitor VLA inference node status updates."""
        status = msg.data
        self.get_logger().info(f"VLA status: {status}")

        if self._state == OrchestratorState.INFERENCE:
            if status == VlaStatus.DONE:
                self.get_logger().info("VLA inference complete → transitioning to handoff")
                if self._auto_handoff:
                    self._transition_to(OrchestratorState.HANDOFF)
                else:
                    self.get_logger().info("Waiting for user trigger before handoff")
                    # Could publish a "READY_FOR_HANDOFF" state here
                    
            elif status == VlaStatus.ERROR:
                self.get_logger().error("VLA inference failed")
                self._transition_to(OrchestratorState.ERROR)

    # ── State Machine ────────────────────────────────────────────────────────

    def _transition_to(self, new_state: OrchestratorState):
        """Transition to a new state and handle state entry logic."""
        if new_state == self._state:
            return

        self.get_logger().info(f"State transition: {self._state} → {new_state}")
        old_state = self._state
        self._state = new_state
        self._state_start_time = time.time()

        # State entry actions
        if new_state == OrchestratorState.HANDOFF:
            self._begin_handoff()
        elif new_state == OrchestratorState.HOMING:
            self._begin_homing()
        elif new_state == OrchestratorState.ERROR:
            self._begin_error_handling()

        self._publish_state()

    def _state_machine_tick(self):
        """Called every 100ms to handle timeouts and state transitions."""
        elapsed = time.time() - self._state_start_time

        if self._state == OrchestratorState.HANDOFF:
            if elapsed > self._handoff_timeout:
                self.get_logger().warn("Handoff timeout — proceeding to home")
                self._transition_to(OrchestratorState.HOMING)

        elif self._state == OrchestratorState.HOMING:
            if elapsed > self._home_timeout:
                self.get_logger().warn("Homing timeout — returning to idle")
                self._transition_to(OrchestratorState.IDLE)

    # ── State Actions ────────────────────────────────────────────────────────

    def _begin_handoff(self):
        """
        VLA inference is done. Move to preset poses via MoveIt.
        This might involve:
        - Moving to a "place" position
        - Opening/closing gripper
        - Moving to a safe retreat position
        """
        self.get_logger().info("Beginning handoff phase")
        
        # First, retreat to safe position
        self._move_to_pose(self._cfg.retreat_pose, "retreat position")
        
        # Then handle task-specific actions
        if self._current_command:
            command = self._current_command.get("command", "").lower()
            
            if "pick" in command or "grab" in command:
                # Object should now be grasped — determine where to place it
                place_location = self._determine_place_location(command)
                try:
                    place_pose = self._cfg.get_place_pose(place_location)
                    self._move_to_pose(place_pose, f"place position ({place_location})")
                    
                    # Open gripper to release object after a brief pause
                    def release_object():
                        time.sleep(1.0)  # Give time for movement to complete
                        if self._state == OrchestratorState.HANDOFF:
                            self._open_gripper()
                            
                    import threading
                    threading.Thread(target=release_object, daemon=True).start()
                    
                except KeyError as e:
                    self.get_logger().warn(f"Unknown place location: {e}")
                    # Fall back to default retreat
                    pass

        # Auto-advance to homing after configured pause
        def advance_to_home():
            time.sleep(self._cfg.retreat_pause_s)
            if self._state == OrchestratorState.HANDOFF:
                self._transition_to(OrchestratorState.HOMING)
        
        import threading
        threading.Thread(target=advance_to_home, daemon=True).start()

    def _begin_homing(self):
        """Send arm back to home position."""
        self.get_logger().info("Returning to home position")
        
        # Open gripper before homing for safety
        self._open_gripper()
        
        # Move to home pose
        self._move_to_pose(self._cfg.home_pose, "home position")
        
        # Complete homing after configured delay
        def complete_home():
            time.sleep(self._cfg.homing_pause_s)
            if self._state == OrchestratorState.HOMING:
                self.get_logger().info("Homing complete — ready for next command")
                self._transition_to(OrchestratorState.IDLE)
        
        import threading
        threading.Thread(target=complete_home, daemon=True).start()

    def _begin_error_handling(self):
        """Handle error states — stop everything and move to safe position."""
        self.get_logger().error("Entering error state — stopping all motion")
        
        # Safety actions
        if self._cfg.safety_open_gripper_on_error:
            self._open_gripper()
        
        # Move to emergency position
        self._move_to_pose(self._cfg.emergency_pose, "emergency position")
        
        # TODO: Send stop commands to active controllers
        # TODO: Could auto-recover to IDLE after a timeout

    # ── Action Primitives ────────────────────────────────────────────────────

    def _open_gripper(self):
        """Open the gripper."""
        msg = Float64()
        msg.data = self._gripper_open
        self._gripper_pub.publish(msg)
        self.get_logger().info("Gripper opened")

    def _close_gripper(self):
        """Close the gripper."""
        msg = Float64()
        msg.data = self._gripper_closed
        self._gripper_pub.publish(msg)
        self.get_logger().info("Gripper closed")

    def _move_to_pose(self, pose: Pose, description: str = "target"):
        """
        Move to a specified pose using the goal_pose publisher.
        
        Args:
            pose: (position, orientation) tuple from coordinator config
            description: Human-readable description for logging
        """
        position, orientation = pose
        
        pose_msg = PoseStamped()
        pose_msg.header.frame_id = "world"
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        
        # Set position
        pose_msg.pose.position.x = position[0]
        pose_msg.pose.position.y = position[1] 
        pose_msg.pose.position.z = position[2]
        
        # Set orientation (quaternion)
        pose_msg.pose.orientation.x = orientation[0]
        pose_msg.pose.orientation.y = orientation[1]
        pose_msg.pose.orientation.z = orientation[2]
        pose_msg.pose.orientation.w = orientation[3]
        
        self._goal_pose_pub.publish(pose_msg)
        self.get_logger().info(f"Moving to {description}: {position}")

    def _determine_place_location(self, command: str) -> str:
        """
        Determine where to place an object based on the command text.
        
        Args:
            command: The original voice command text
            
        Returns:
            Key for place_positions dict
        """
        command_lower = command.lower()
        
        # Simple keyword matching — could be expanded with NLP
        if "bin" in command_lower or "trash" in command_lower:
            return "bin"
        elif "shelf" in command_lower or "shelve" in command_lower:
            return "shelf"
        elif "center" in command_lower or "middle" in command_lower:
            return "table_center"
        elif "drop" in command_lower:
            return "drop_zone"
        else:
            # Default fallback
            return "bin"

    # ── Publishing ────────────────────────────────────────────────────────────

    def _publish_state(self):
        """Publish current state for monitoring/debugging."""
        msg = String()
        msg.data = self._state
        self._state_pub.publish(msg)


# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = OrchestratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()