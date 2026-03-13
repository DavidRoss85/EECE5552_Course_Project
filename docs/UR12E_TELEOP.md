# UR12e Simulator Teleoperation

This guide explains how to teleoperate the UR12e in the Gazebo simulator using a joystick and MoveIt Servo.

---

## Overview

Teleoperation uses real-time twist commands (linear and angular velocity) to drive the arm. The data flow is:

```
Joystick → joy_node → teleop_twist_joy → teleop_controller → MoveIt Servo → UR12e
                         /cmd_vel         /servo_node/delta_twist_cmds
```

- **joy_node**: Publishes raw joystick axes/buttons
- **teleop_twist_joy**: Maps joystick input to Twist (`/cmd_vel`)
- **teleop_controller**: Converts Twist to TwistStamped for Servo (`/servo_node/delta_twist_cmds`)
- **MoveIt Servo**: Sends velocity commands to the simulated arm

---

## Prerequisites

1. **Simulation running** — Gazebo with UR12e, MoveIt, and Servo launched (see [simulation/README.md](../simulation/README.md))
2. **Joystick connected** — USB gamepad or compatible controller
3. **Packages installed**:
   ```bash
   sudo apt install ros-jazzy-joy ros-jazzy-teleop-twist-joy
   ```

---

## Launch Order

### Step 1 — Simulation (Terminal 1)

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/sim.launch.py
```

Wait for "You can start planning now!"

---

### Step 2 — Set Command Type (Terminal 2)

Switch Servo to accept twist commands (required for teleop):

```bash
source /opt/ros/jazzy/setup.bash
./scripts/set_command_type.sh
```

Or call the service directly:
```bash
ros2 service call /servo_node/switch_command_type moveit_msgs/srv/ServoCommandType "{command_type: 1}"
```

---

### Step 3 — Planning Scene (Terminal 3, optional)

Add the table as a collision object so the arm avoids it:

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 run robot_control environment_setup
```

---

### Step 4 — Joystick Node (Terminal 4)

```bash
source /opt/ros/jazzy/setup.bash
ros2 run joy joy_node --ros-args -p use_sim_time:=true
```

Or use the helper script:
```bash
source /opt/ros/jazzy/setup.bash
./scripts/start_joystick.sh
```

---

### Step 5 — Teleop Twist Joy (Terminal 5)

```bash
source /opt/ros/jazzy/setup.bash
ros2 run teleop_twist_joy teleop_node --ros-args \
  -p require_enable_button:=false \
  -p use_sim_time:=true
```

Or use the helper script:
```bash
source /opt/ros/jazzy/setup.bash
./scripts/start_teleop.sh
```

---

### Step 6 — Teleop Controller (Terminal 6)

Bridges `/cmd_vel` to `/servo_node/delta_twist_cmds` for MoveIt Servo:

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 run robot_control teleop_controller --ros-args -p use_sim_time:=true
```

---

## Using the Joystick

With the default `teleop_twist_joy` mapping:

| Input            | Effect                               |
|------------------|--------------------------------------|
| Left stick X     | Linear velocity in Y (left/right)    |
| Left stick Y     | Linear velocity in X (forward/back)  |
| Right stick      | Angular velocity (rotation)          |

Move the sticks to drive the end effector. Servo applies velocity limits from its config for safety.

---

## Troubleshooting

**Robot doesn't move**
- Check Servo is receiving robot state (no repeated "Waiting to receive robot state update" in the servo logs)
- Verify topics: `ros2 topic list | grep -E "cmd_vel|delta_twist|joy"`

**Servo keeps "Waiting to receive robot state update"**
- Confirm `/joint_states` is publishing: `ros2 topic hz /joint_states`

**Joystick not detected**
- Check device: `ls /dev/input/js*`
- Ensure permissions: `sudo usermod -aG input $USER` and log out/in

**Teleop mapping feels wrong**
- Edit `teleop_twist_joy` parameters (scale, axis mappings) or create a custom config

---

## Related

- [Simulation README](../simulation/README.md) — Full sim setup and goal-based control
- `scripts/send_goal.py` — Send pose goals (MoveIt planning) instead of teleop
