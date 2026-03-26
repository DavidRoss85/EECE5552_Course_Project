# EECE5552 Course Project

UR12e simulation and teleoperation for ROS 2 Jazzy.

## Quick Start

```bash
# Build
colcon build --packages-select robot_control
source install/setup.bash

# Launch sim (Gazebo + MoveIt + Servo, ~30 s to full startup)
ros2 launch launch/sim.launch.py

# Launch teleop (joystick)
ros2 launch launch/teleop.launch.py

# Or for LeRobot recording: teleop_joy_for_lerobot + lerobot-teleoperate (see docs/UR12E_LEROBOT.md)
```

## Documentation

| Doc | Description |
|-----|-------------|
| [simulation/README.md](simulation/README.md) | Simulation setup, launch order, goal-based control |
| [docs/UR12E_TELEOP.md](docs/UR12E_TELEOP.md) | Joystick teleop, B-button home, mapping |
| [docs/UR12E_TELEOP_GRIPPER_SETUP.md](docs/UR12E_TELEOP_GRIPPER_SETUP.md) | Current teleop + gripper wiring and debug flow |
| [docs/UR12E_LEROBOT.md](docs/UR12E_LEROBOT.md) | LeRobot recording (ros_twist, ur12e_ros) |
| [docs/SO101_IMITATION_LEARNING.md](docs/SO101_IMITATION_LEARNING.md) | SO101 imitation learning POC |
| [docs/UR12E_GAZEBO_SETUP.md](docs/UR12E_GAZEBO_SETUP.md) | UR simulator installation (apt) |
| [docs/UR12E_REFERENCE.md](docs/UR12E_REFERENCE.md) | Robot reference (joints, frames) |
| [docs/MOVEIT_PUBLISHER_NODE.md](docs/MOVEIT_PUBLISHER_NODE.md) | MoveIt publisher node |
