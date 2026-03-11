# UR12e Reference — Joint Names & Documentation Sources

This document is a reference for the Universal Robots **UR12e** as used in this project with ROS 2 Jazzy: joint names, planning group, and where those are defined in the official packages.

---

## Overview

The UR12e is a 6-DOF collaborative robot. In ROS 2 it uses the same joint naming and planning-group conventions as other UR e-series arms (UR3e, UR5e, UR10e, etc.). The robot description and MoveIt configuration come from the official Universal Robots ROS 2 packages; this project does not ship its own URDF or SRDF.

---

## Joint Names (6-DOF)

The arm has six revolute joints. These names are used in the URDF, `/joint_states`, and MoveIt (e.g. `JointConstraint` in motion planning).

| # | Joint name             | Description / typical role        |
|---|------------------------|-----------------------------------|
| 1 | `shoulder_pan_joint`   | Base rotation (yaw); arm swings left/right |
| 2 | `shoulder_lift_joint`  | Shoulder elevation; arm raises/lowers      |
| 3 | `elbow_joint`          | Elbow bend                         |
| 4 | `wrist_1_joint`        | First wrist joint                  |
| 5 | `wrist_2_joint`        | Second wrist joint                 |
| 6 | `wrist_3_joint`        | Third wrist joint (tool flange rotation)   |

All angles are in **radians** in ROS 2 (e.g. in `sensor_msgs/JointState`, `moveit_msgs/JointConstraint`).

---

## Planning Group: `ur_manipulator`

In the official MoveIt configuration for UR robots, the arm is exposed as the planning group **`ur_manipulator`**, which includes all six joints above. When sending a `MotionPlanRequest` (e.g. from the `moveit_publisher` node), use:

- **`group_name`** = `"ur_manipulator"`

Joint names in your goal constraints must match the names above (e.g. `shoulder_pan_joint`, not `shoulder_pan`).

---

## Where the Joints Are Documented

The joint names and limits are **not** defined in this repository. They come from the following official sources.

### 1. Robot description (URDF / xacro)

- **Package:** `ur_description` (pulled in by `ur_simulation_gz`, `ur_robot_driver`, etc.)
- **Repository:** [UniversalRobots/Universal_Robots_ROS2_Description](https://github.com/UniversalRobots/Universal_Robots_ROS2_Description)
- **Relevant files:**
  - `urdf/ur.urdf.xacro` — top-level scene/robot xacro
  - `urdf/inc/ur_macro.xacro` — macro that defines the kinematic chain and joint names for each UR model (ur3e, ur5e, ur10e, ur12e, etc.)

The URDF/xacro is the source of truth for joint names in the robot model.

### 2. Joint limits and MoveIt config

- **Repository:** [UniversalRobots/Universal_Robots_ROS2_Driver](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver)
- **Relevant files:**
  - `ur_moveit_config/config/joint_limits.yaml` — joint names, limits, and scaling (used by MoveIt)
  - SRDF and other config under `ur_moveit_config` — define planning groups (e.g. `ur_manipulator`) and which joints they contain

Same joint names appear here as in the URDF; this is what MoveIt uses for planning.

### 3. Official documentation

- **Universal Robots ROS 2:** [Universal Robots ROS 2 Documentation](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/)
- **ROS 2 package index:** [ur_description](https://index.ros.org/p/ur_description/)
- **API docs (Humble):** [ur_description — ROS 2 Humble](https://docs.ros.org/en/ros2_packages/humble/api/ur_description/index.html)

---

## Checking Joint Names at Runtime

To see the exact joint names and current values on a running system:

```bash
# Current joint state (names and positions)
ros2 topic echo /joint_states --once
```

To inspect planning groups and joint names from the MoveIt side (when MoveIt is running):

```bash
ros2 param get /move_group robot_description_planning_groups
```

---

## Relation to This Project

- **Launch and simulation:** See [UR12E_GAZEBO_SETUP.md](UR12E_GAZEBO_SETUP.md) for installing and launching the UR12e in Gazebo with `ur_simulation_gz`.
- **Motion planning:** The `moveit_publisher` node in the `moveit_examples` package sends goals to the `ur_manipulator` group using these joint names; see [MOVEIT_PUBLISHER_NODE.md](MOVEIT_PUBLISHER_NODE.md).

When adding or editing joint constraints (e.g. in `moveit_publisher.py`), use the six names listed in the table above and the group name `ur_manipulator`.
