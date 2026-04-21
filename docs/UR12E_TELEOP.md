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

**Physical UR12e or URSim** — the repo’s **main entry point** for the UR driver **with** joystick teleop enabled is **`launch/ursim_with_joy_teleop.launch.py`** (UR ROS 2 driver + MoveIt + Servo + `joy_node` / `teleop_twist_joy` / `home_button_node`). Example: `ros2 launch launch/ursim_with_joy_teleop.launch.py robot_ip:=<CONTROLLER_IP>`. For driver only, use `ursim.launch.py`. Details: [README — Bring up the arm stack](../README.md#bring-up-the-arm-stack).

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
| **B button** | **Return to home pose** (ROS trajectory, not LeRobot) |

The enable button (RB / right bumper) must be held to send twist commands. Press **B** to return the arm to the home pose; the node switches controllers, runs the trajectory, then restores Servo control.

> **WARNING — B button vs ML / imitation learning**  
> Home is commanded by **`home_button_node`**, not through LeRobot’s teleop stream. **Recorded episodes do not faithfully encode that motion as training actions** (trim or exclude those segments if they appear).  
> **WARNING — motion can be brisk**  
> Home is a **fixed-time** joint trajectory (**6 s** in code). If the arm is **far from home**, joint speeds can be **high**—**bring the arm close to home first**, clear people and obstacles, then press **B**.

**Home configuration (degrees)** — targets in [`home_button_node.py`](../src/robot_control/robot_control/home_button_node.py) (`HOME_JOINTS`, order `shoulder_pan_joint` … `wrist_3_joint`): **179.9°, −90.0°, 90.0°, −90.0°, −90.0°, 90.0°** (rounded from the radian literals in the file).

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

## LeRobot Recording

For imitation learning with LeRobot (record → train → evaluate), use `teleop_joy_for_lerobot.launch.py` (Gazebo) or `teleop_joy_lerobot_ursim.py` (via `ursim_with_joy_teleop.launch.py` on hardware/URSim—the `ursim` filename is not simulator-only) and `lerobot-teleoperate` with `ros_twist`. Edit `teleop_twist_joy` parameters for your gamepad. **B-button home** is ROS-only and not a valid training action—see **[UR12E_LEROBOT.md — Joystick Mapping](UR12E_LEROBOT.md#joystick-mapping)** for warnings, home joint angles (degrees), and workflow.

**Teleop-only tryout:** hardware path = `ursim_with_joy_teleop.launch.py` + `lerobot-teleoperate --robot.type=ur12e_ros --teleop.type=ros_twist` (see [README — Smoke test](../README.md#smoke-test-teleop-only-lerobot)). **`ur12e_ros`** / **`ros_twist`** are custom `lerobot-ros` plugins; **`ros_twist`** consumes **`Twist`** on `/game_controller`, and **`ur12e_ros`** emits **`TwistStamped`** to MoveIt Servo—see **[UR12E_LEROBOT.md — Custom plugins…](UR12E_LEROBOT.md#custom-plugins-and-moveit-servo-control-path)**.

---

## Related

- [UR12E_LEROBOT.md](UR12E_LEROBOT.md) — LeRobot recording with ros_twist
- [simulation/README.md](../simulation/README.md) — Sim setup and goal-based control
- `scripts/send_goal.py` — Pose goals via MoveIt
