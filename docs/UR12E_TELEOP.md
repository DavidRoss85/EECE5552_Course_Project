# UR12e Joystick Teleoperation

Teleoperate the UR12e in Gazebo using an Xbox or compatible joystick and MoveIt Servo.

---

## Overview

Data flow:

```
Joystick → joy_node → teleop_twist_joy → teleop_controller → MoveIt Servo → UR12e
                         /game_controller   /servo_node/delta_twist_cmds
```

- **joy_node**: Raw joystick axes/buttons → `/joy`
- **teleop_twist_joy**: Maps axes to Twist → `/game_controller`
- **teleop_controller**: Twist → TwistStamped for Servo; **B button** → return to home
- **MoveIt Servo**: Velocity commands → arm

---

## Prerequisites

1. **Simulation running** — `sim.launch.py` brings up Gazebo, MoveIt, Servo, and runs setup (env, home pose, controller switch). Wait ~30 seconds for it to finish.
2. **Joystick** — USB gamepad (e.g. Xbox Series X Controller)
3. **Packages:**
   ```bash
   sudo apt install ros-jazzy-joy ros-jazzy-teleop-twist-joy
   ```

---

## Launch

### 1. Simulation (Terminal 1)

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/sim.launch.py
```

Wait for the full startup sequence (~30 s).

### 2. Teleop (Terminal 2)

```bash
source /opt/ros/jazzy/setup.bash
source ~/EECE5552_Course_Project/install/setup.bash
ros2 launch launch/teleop.launch.py
```

This starts joy_node, teleop_twist_joy, and teleop_controller.

---

## Joystick Mapping (Xbox)

| Input | Effect |
|-------|--------|
| Left stick X | Left / right |
| Left stick Y | Forward / back |
| Right stick Y | Up / down |
| Right stick X | Rotate (yaw) |
| **B button** | **Return to home pose** |

The enable button (RB / right bumper) must be held to send twist commands. Press **B** to return the arm to the home pose; the node switches controllers, runs the trajectory, then restores Servo control.

---

## Topic Flow

```
/joy (sensor_msgs/Joy)
    ↓
teleop_twist_joy → /game_controller (geometry_msgs/Twist)
    ↓
teleop_controller → /servo_node/delta_twist_cmds (geometry_msgs/TwistStamped)
    ↓
servo_node → /forward_position_controller/commands
    ↓
UR12e in Gazebo
```

---

## Alternative: Keyboard Teleop

```bash
sudo apt install ros-jazzy-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

`teleop_controller` subscribes to `/game_controller`. Remap teleop_twist_keyboard to publish there, or change teleop_controller to subscribe to `/cmd_vel`.

---

## Troubleshooting

**Robot doesn't move**
- Hold the enable button (A)
- Check topics: `ros2 topic list | grep -E "game_controller|delta_twist|joy"`
- Ensure Servo receives state (no repeated "Waiting to receive robot state update")

**Joystick not detected**
- `ls /dev/input/js*`
- `sudo usermod -aG input $USER` and log out/in

**Constant drift / rotation**
- teleop_controller uses a deadzone; axis mapping may need tuning in `teleop.launch.py`

**B button home fails**
- Sim must be fully up; trajectory controller is switched in briefly

---

## Related

- [simulation/README.md](../simulation/README.md) — Sim setup and goal-based control
- `scripts/send_goal.py` — Pose goals via MoveIt
