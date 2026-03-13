# Teleop in Simulation — Setup Guide

This guide covers how to manually teleoperate the UR12e arm in Gazebo using MoveIt Servo.

---

## Prerequisites

Install keyboard teleop if not already installed:

```bash
sudo apt install ros-jazzy-teleop-twist-keyboard
```

---

## Step 1 — Launch the Simulation

```bash
cd ~/EECE5552_Course_Project
ros2 launch launch/sim.launch.py
```

Wait about 15 seconds for Gazebo, MoveIt, RViz, and servo_node to fully come up.

---

## Step 2 — Move Arm Out of Singularity

The arm starts in an upright home position which is a singularity. Servo will emergency-stop if you try to move from there. Use the trajectory controller (active by default) to move it to a safe "elbow up" pose first:

```bash
ros2 action send_goal /scaled_joint_trajectory_controller/follow_joint_trajectory control_msgs/action/FollowJointTrajectory "{trajectory: {joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint], points: [{positions: [0.0, -1.5707, 1.5707, -1.5707, -1.5707, 0.0], time_from_start: {sec: 3, nanosec: 0}}]}}"
```

---

## Step 3 — Switch to Forward Position Controller

MoveIt Servo publishes to `/forward_position_controller/commands`. The trajectory controller and the forward position controller cannot share joints, so you need to swap them:

```bash
# Spawn and activate forward_position_controller
ros2 run controller_manager spawner forward_position_controller

# Deactivate the trajectory controller
ros2 control set_controller_state scaled_joint_trajectory_controller inactive
```

Verify with:
```bash
ros2 control list_controllers
```
`forward_position_controller` should be `active` and `scaled_joint_trajectory_controller` should be `inactive`.

---

## Step 4 — Set Servo Command Type to Twist

```bash
bash ~/EECE5552_Course_Project/scripts/set_command_type.sh
```

This calls `/servo_node/switch_command_type` with `command_type: 1` (TWIST mode).

---

## Step 5 — Run the Teleop Controller Node

**Terminal 2:**
```bash
cd ~/EECE5552_Course_Project
source install/setup.bash
ros2 run robot_control teleop_controller
```

This node bridges `/cmd_vel` (Twist) → `/servo_node/delta_twist_cmds` (TwistStamped) with `frame_id: tool0`, meaning commands are relative to the end-effector frame.

---

## Step 6 — Run Keyboard Teleop

**Terminal 3:**
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

## Topic Map

```
teleop_twist_keyboard
        |
        v
     /cmd_vel  (geometry_msgs/Twist)
        |
        v
  teleop_controller  [robot_control pkg]
        |
        v
  /servo_node/delta_twist_cmds  (geometry_msgs/TwistStamped, frame_id: tool0)
        |
        v
    servo_node  [MoveIt Servo]
        |
        v
  /forward_position_controller/commands
        |
        v
     UR12e in Gazebo
```

---

## Troubleshooting

**Servo not moving / singularity emergency stop**
Run Step 2 to move the arm to a non-singular pose before switching controllers.

**`/forward_position_controller/commands` not receiving data**
Make sure `teleop_controller` is running (Step 5) and `set_command_type.sh` was called (Step 4).

**`ros2 control list_controllers` shows `forward_position_controller` as `unconfigured`**
Use `spawner` as shown in Step 3, not `set_controller_state`.

**servo_node services hang**
This happens when servo_node launches before `robot_description` is available. Restart the sim — the launch file delays servo_node by 10 seconds to avoid this.
