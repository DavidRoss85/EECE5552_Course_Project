# UR12e Gazebo Simulator — Installation & Launch Guide

This guide documents how to install and launch the Universal Robots UR12e in Gazebo simulation using the official `ur_simulation_gz` package on **ROS 2 Jazzy**.

**Sources:**

- [Installation — Universal Robots ROS 2 Driver](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_simulation_gz/ur_simulation_gz/doc/installation.html)
- [Usage — Universal Robots ROS 2 Driver](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_simulation_gz/ur_simulation_gz/doc/usage.html)

---

## Installation

1. Install ROS 2 Jazzy: [ROS 2 Jazzy Ubuntu Installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debians.html)

2. Install the UR robot driver (required):
   ```bash
   sudo apt install ros-jazzy-ur-robot-driver
   ```

3. Install the simulation package:
   ```bash
   sudo apt-get install ros-jazzy-ur-simulation-gz
   ```

4. Source your ROS 2 Jazzy installation:
   ```bash
   source /opt/ros/jazzy/setup.bash
   ```

---

## Launching the UR12e Simulator

Two launch files are available:

| Launch File | Gazebo | RViz | MoveIt! |
|-------------|--------|------|---------|
| `ur_sim_control.launch.py` | ✓ | ✓ | ✗ |
| `ur_sim_moveit.launch.py` | ✓ | ✓ | ✓ |

### Basic launch (Gazebo + RViz only)

For simulation without motion planning:

```bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur12e
```

To test motion with the example script (uses the `ur_robot_driver` installed above), in a new terminal:

```bash
ros2 run ur_robot_driver example_move.py
```

### Full launch (Gazebo + RViz + MoveIt!)

For simulation with MoveIt! motion planning:

```bash
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py ur_type:=ur12e
```

This enables planning via MoveGroup interfaces or the Motion Planning panel in RViz.

---

## Customization Options

### Custom robot/scene description

```bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur12e \
  description_file:="/path/to/your/robot.urdf.xacro" \
  rviz_config_file:="/path/to/your/config.rviz"
```

### Custom world (SDF)

To use a custom Gazebo world instead of the default empty world:

```bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur12e \
  world_file:=/path/to/your/world.sdf
```

With MoveIt!:

```bash
ros2 launch ur_simulation_gz ur_sim_moveit.launch.py ur_type:=ur12e \
  world_file:=/path/to/your/world.sdf
```

### TF prefix

For `ur_sim_control.launch.py` only (not available with MoveIt! launch), you can specify a `tf_prefix` by defining a custom controllers file and passing it with `controllers_file`. See the [official documentation](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_simulation_gz/ur_simulation_gz/doc/usage.html#tf-prefix) for the required YAML format.

---

## References

- [Installation — Universal Robots ROS 2 Driver](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_simulation_gz/ur_simulation_gz/doc/installation.html)
- [Usage — Universal Robots ROS 2 Driver](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_simulation_gz/ur_simulation_gz/doc/usage.html)
- [Gazebo SDF Worlds Tutorial](https://gazebosim.org/docs/harmonic/sdf_worlds)
