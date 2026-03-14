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
```

## Documentation

| Doc | Description |
|-----|-------------|
| [simulation/README.md](simulation/README.md) | Simulation setup, launch order, goal-based control |
| [docs/UR12E_TELEOP.md](docs/UR12E_TELEOP.md) | Joystick teleop, B-button home, mapping |
| [docs/UR12E_GAZEBO_SETUP.md](docs/UR12E_GAZEBO_SETUP.md) | UR simulator installation (apt) |
| [docs/UR12E_REFERENCE.md](docs/UR12E_REFERENCE.md) | Robot reference (joints, frames) |
| [docs/MOVEIT_PUBLISHER_NODE.md](docs/MOVEIT_PUBLISHER_NODE.md) | MoveIt publisher node |
Course project files.

## Documentation

- [SO101 Imitation Learning POC](docs/SO101_IMITATION_LEARNING.md) — Imitation learning POC on the SO-101 (LeRobot) done prior to trying it on the UR12e
- [UR12E Gazebo Setup](docs/UR12E_GAZEBO_SETUP.md) — Gazebo simulation setup
- [UR12E Teleop](docs/UR12E_TELEOP.md) — Teleoperation with joystick and MoveIt Servo
- [Simulation](simulation/README.md) — Simulation launch and usage
