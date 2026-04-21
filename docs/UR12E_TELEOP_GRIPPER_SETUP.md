# UR12e Teleop + Gripper Setup (Current)

This document captures the current UR12e teleop and gripper behavior in this repository, including how LeRobot records arm/gripper signals and how to debug "gripper works but arm does not move".

## Scope

- ROS 2 Jazzy
- UR12e via **`launch/ursim_with_joy_teleop.launch.py`** (main entry: driver + teleop) or `launch/ursim.launch.py` (driver only)
- Joystick teleop via `launch/teleop_joy_lerobot_ursim.py`
- LeRobot with:
  - `--robot.type=ur12e_ros`
  - `--teleop.type=ros_twist`

## Runtime Architecture

### Arm motion path

```text
/joy
  -> teleop_twist_joy (RB deadman gate)
  -> /game_controller (Twist)
  -> ros_twist teleoperator (LeRobot)
  -> ur12e_ros robot interface
  -> /servo_node/delta_twist_cmds (TwistStamped)
  -> MoveIt Servo
  -> /forward_position_controller/commands
  -> UR arm joints
```

### Gripper motion path

```text
/joy (A button edge)
  -> home_button_node
  -> /gripper_controller/gripper_cmd (GripperCommand action)
  -> gripper_moveit_bridge
  -> Robotiq socket commands
```

There is also a LeRobot gripper command stream:

```text
/joy (button index from ros_twist config)
  -> ros_twist teleoperator
  -> action["gripper.pos"]
  -> ur12e_ros gripper topic mode
  -> /gripper_position (Float64)
```

## Gripper Semantics and Control Modes

The current stack has two gripper control paths that can run at the same time.

## Low-Level Robotiq Socket Activation

The gripper is activated and commanded over a dedicated TCP socket endpoint instead of standard arm joint control.

- Node: `src/robot_control/robot_control/gripper_moveit_bridge.py`
- Target: `<robot_ip>:63352` (configurable via `gripper_port`, defaults to `63352`)
- Transport: plain UTF-8 text commands, newline-terminated
- Startup behavior: controlled by `activate_gripper_on_start` (set `True` in `launch/ursim.launch.py`)

### Activation handshake (sent on startup)

When `gripper_moveit_bridge` starts, it runs this sequence:

1. `SET ACT 1`
2. `SET MOD 0`
3. `SET GTO 1`
4. `SET SPE 255`
5. `SET FOR 255`

This is the low-level Robotiq bring-up sequence used before open/close commands.

### Runtime position commands

After activation, the bridge sends:

- Open:
  - `SET GTO 1`
  - `SET POS 0`
- Close:
  - `SET GTO 1`
  - `SET POS 255`

`gripper_moveit_bridge` maps higher-level ROS action/topic inputs to these socket commands.

### 1) Physical toggle path (`home_button_node`)

- Source: `src/robot_control/robot_control/home_button_node.py`
- Trigger: `A_BUTTON_IDX = 0`
- Transport: `GripperCommand` action on `/gripper_controller/gripper_cmd`
- Execution: `gripper_moveit_bridge` sends Robotiq socket commands (`SET POS ...`)

Behavior details:

- `home_button_node` stores `_gripper_open` state and toggles on A rising edge
- It sends:
  - `goal.command.position = 0.0` when transitioning open -> closed
  - `goal.command.position = 1.0` when transitioning closed -> open
- In `gripper_moveit_bridge`, action goals are interpreted with `open_threshold = 0.5`:
  - `position >= 0.5` -> open
  - `position < 0.5` -> close
- Bridge maps this to socket-level Robotiq positions:
  - open -> `SET POS 0`
  - close -> `SET POS 255`

**B button (arm home, same node)** — `B_BUTTON_IDX = 1` runs a **joint-space home trajectory** via `scaled_joint_trajectory_controller`, not through LeRobot.

> **WARNING** — Home is **outside the ML action stream**; datasets do not faithfully record that motion (trim or skip affected episodes). The trajectory is **6 s** fixed duration—if the arm is **far from home**, motion toward these targets can be **fast** in joint space; **start near home** and clear the workspace before pressing **B**. Joint targets in **degrees** (same order as `HOME_JOINTS` in code): shoulder pan **179.9**, shoulder lift **−90.0**, elbow **90.0**, wrist_1 **−90.0**, wrist_2 **−90.0**, wrist_3 **90.0**. Full context: [UR12E_LEROBOT.md — Joystick Mapping](UR12E_LEROBOT.md#joystick-mapping).

### 2) LeRobot command path (`ros_twist` + `ur12e_ros`)

- Source teleop: `lerobot-ros/lerobot_teleoperator_devices/.../ros_twist.py`
- Source robot IO: `lerobot-ros/lerobot_robot_ros/.../ros_interface.py`
- Trigger button: `gripper_button` in `config_ros_twist.py` (currently index `2`)
- Transport: Float topic `/gripper_position`

Behavior details:

- `ros_twist` maintains `_gripper_pos` and toggles it on button rising edge
- Convention in LeRobot path:
  - `gripper.pos = 0.0` -> closed
  - `gripper.pos = 1.0` -> open
- In `ur12e_ros` config, gripper mode is `TOPIC`, so LeRobot publishes `Float64` directly to `/gripper_position`
- `gripper_moveit_bridge` topic callback enforces strict values:
  - `1.0` -> open
  - `0.0` -> close
  - other values -> rejected with warning

## Important Mapping Note (A button vs recorded gripper)

Because physical actuation and LeRobot teleop are separate inputs:

- Pressing A can move the physical gripper via `home_button_node`
- LeRobot only records gripper changes when its own `ros_twist` gripper state changes
- If you want A press to be both physical actuation and recorded command, align teleop config:
  - set `gripper_button = 0` in `config_ros_twist.py`, or
  - pass an equivalent runtime override

## Current Button Mapping (from code)

### `launch/teleop_joy_lerobot_ursim.py`

Despite **`ursim` in the path**, this launch is the **same joy + `teleop_twist_joy` + `home_button_node` stack** used for live hardware when you start `ursim_with_joy_teleop.launch.py` (driver + MoveIt + Servo + teleop). It is not limited to URSim.

Defaults target an **older Xbox-style** gamepad; other controllers usually need **`enable_button` and `axis_linear.*` changes** in this file. Confirm behavior in **Gazebo or URSim** before trusting the mapping on a physical arm.

- Deadman/enable button: `7` (RB on typical Xbox mapping)
- Twist topic remap: `/cmd_vel` → `/game_controller`
- Axis config (current code):
  - `axis_linear.x = 0`
  - `axis_linear.y = 1`
  - `axis_linear.z = 3`
  - `scale_linear.x/y/z` set to `-0.5`, `0.5`, `-0.5` respectively (see file for exact values)

### `src/robot_control/robot_control/home_button_node.py`

- `A_BUTTON_IDX = 0`: toggles gripper open/close
- `B_BUTTON_IDX = 1`: sends arm to home pose (controller switch flow)

### `lerobot-ros/lerobot_teleoperator_devices/.../config_ros_twist.py`

- `gripper_button = 2` (X by default in current code)

This means physical gripper actuation and LeRobot gripper command capture can be driven by different buttons unless you explicitly align them.

## What LeRobot Records

Dataset metadata is in:

- `meta/info.json` (feature names/layout)
- `meta/stats.json` (min/max/mean/std per feature)

### Key checks

1. Confirm action layout includes gripper:
   - `meta/info.json` -> `features.action.names` contains `"gripper.pos"`
2. Confirm gripper action changed:
   - `meta/stats.json` -> `action.min[6]` and `action.max[6]`
   - If different (for example `0` and `1`), gripper command changes were captured

### Notes

- `action` is the control signal used for training targets
- `observation.state` is measured/estimated robot state
- In this setup, `observation.state.gripper.pos` is not hard gripper encoder feedback
- For `ur12e_ros` TOPIC mode, `observation.state.gripper.pos` is derived from the last commanded gripper value inside `ros_interface.py`

### What to trust for training/debug

- Use `action[6]` (`gripper.pos`) to confirm captured control intent
- Use `observation.state.gripper.pos` as command-state context, not definitive hardware truth

## Quick Test Script

Use:

- `scripts/ur12e/record_test_no_cameras.sh`

It records a short, no-camera dataset for fast validation.

## "Gripper Works, Arm Won't Move" Debug Order

If `/game_controller` is publishing but arm is static, check this chain in order:

1. LeRobot to Servo:
   - `ros2 topic echo /servo_node/delta_twist_cmds --once`
2. Servo to controller:
   - `ros2 topic echo /forward_position_controller/commands --once`
3. Joint feedback:
   - `ros2 topic echo /joint_states --once`
4. Controller activation:
   - `ros2 control list_controllers`
   - `forward_position_controller` should be active for servo motion
5. UR robot program state:
   - `ros2 topic echo /io_and_status_controller/robot_program_running --once`
   - Must be `true`

If needed, recover program/controller state:

```bash
ros2 service call /io_and_status_controller/resend_robot_program std_srvs/srv/Trigger "{}"
ros2 service call /controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{activate_controllers: ['forward_position_controller'], deactivate_controllers: ['scaled_joint_trajectory_controller'], strictness: 2}"
ros2 service call /servo_node/pause_servo std_srvs/srv/SetBool "{data: false}"
ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 1}"
```

## Source Files

- `launch/ursim_with_joy_teleop.launch.py` (main: driver + teleop)
- `launch/ursim.launch.py`
- `launch/teleop_joy_lerobot_ursim.py`
- `src/robot_control/robot_control/home_button_node.py`
- `src/robot_control/robot_control/gripper_moveit_bridge.py`
- `lerobot-ros/lerobot_teleoperator_devices/lerobot_teleoperator_devices/ros_twist.py`
- `lerobot-ros/lerobot_teleoperator_devices/lerobot_teleoperator_devices/config_ros_twist.py`
- `lerobot-ros/lerobot_robot_ros/lerobot_robot_ros/config.py`
- `lerobot-ros/lerobot_robot_ros/lerobot_robot_ros/ros_interface.py`
