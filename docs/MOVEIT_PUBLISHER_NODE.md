# moveit_publisher Node — Detailed Documentation

The `moveit_publisher` node is a ROS 2 (Jazzy) example that sends a **motion planning request** to MoveIt 2 via the **MoveGroup** action. It demonstrates how to build a `MotionPlanRequest` with joint-space goal constraints and trigger planning (and optional execution) through the MoveIt stack.

---

## Overview

| Property | Value |
|----------|--------|
| **Package** | `moveit_examples` |
| **Executable** | `moveit_publisher` |
| **Node name** | `moveit_client` (as registered in ROS) |
| **Language** | Python |
| **Role** | Action client that sends a single MoveGroup goal at startup |

The node does **not** publish topics in the traditional sense; the name “publisher” here refers to *publishing* a planning request (goal) to the MoveGroup action server. Once the goal is sent asynchronously, the node continues spinning so the action client can receive feedback and result.

---

## How to Run

**Prerequisites:** The MoveIt stack (e.g. MoveItPy or `move_group`) must be running so that the MoveGroup action server is available. See [UR12E_GAZEBO_SETUP.md](UR12E_GAZEBO_SETUP.md) for bringing up the UR12e in Gazebo with MoveIt.

```bash
# From the workspace root, after sourcing the workspace
source install/setup.bash
ros2 run moveit_examples moveit_publisher
```

If the action server is not up, the node will block at startup with:  
`Waiting for MoveGroup action server...`

---

## Architecture

### Class: `MoveGroupClient`

The node is implemented as a single class that subclasses `rclpy.node.Node` and owns an `ActionClient` for the MoveGroup action.

```
┌─────────────────────────────────────────────────────────────────┐
│  moveit_publisher (process)                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  MoveGroupClient (node name: "moveit_client")                 ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │  ActionClient(MoveGroup, "/move_action")                 │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │  Goal (MotionPlanRequest + PlanningOptions)
                              │  Feedback / Result
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  MoveIt (move_group / MoveItPy)                                  │
│  Action server: /move_action (MoveGroup)                         │
└─────────────────────────────────────────────────────────────────┘
```

### Execution Flow

1. **`main()`**  
   - Initializes ROS 2 (`rclpy.init()`).  
   - Instantiates `MoveGroupClient`.  
   - Calls `rclpy.spin(node)` so the node processes callbacks (e.g. action feedback/result).

2. **`__init__()`**  
   - Calls `super().__init__("moveit_client")` so the node appears as `moveit_client` in the graph.  
   - Creates an `ActionClient` for the `MoveGroup` action on the topic **`/move_action`**.  
   - Blocks until the action server is available (`wait_for_server()`).  
   - Calls `send_goal()` once.

3. **`send_goal()`**  
   - Builds a `MoveGroup.Goal()` containing a `MotionPlanRequest` and `PlanningOptions`.  
   - Sends the goal asynchronously (`send_goal_async()`).  
   - Does **not** register callbacks; the node simply spins so the client can receive responses.

---

## Interfaces

### Action client (outgoing)

| Interface | Type | Topic/Action Name | Description |
|-----------|------|-------------------|-------------|
| Action client | `moveit_msgs/action/MoveGroup` | `/move_action` | Sends motion planning requests to MoveIt. |

The **MoveGroup** action is the standard way for MoveIt 2 to accept a motion plan request (and optionally execute it). The goal contains a `MotionPlanRequest` and `PlanningOptions`; the result contains the planned trajectory and status information.

### Topics used implicitly by MoveIt

The node does not subscribe to or publish any topics itself. MoveIt, on the other hand, typically uses:

- **`/joint_states`** — Current robot joint positions. The request uses `start_state.is_diff = True`, which tells MoveIt to *diff* the given start state against the current state (often from `/joint_states`), so the effective start is the current robot configuration.

---

## Goal content: MotionPlanRequest in detail

The node fills a **`MotionPlanRequest`** as follows.

### Planning group

- **`group_name`** = `"ur_manipulator"`  
  Must match a planning group defined in the SRDF (e.g. for a UR12e arm). This is the group MoveIt will plan for.

### Planning time

- **`allowed_planning_time`** = `5.0` (seconds)  
  Maximum time the planner is allowed to spend to find a solution.

### Start state

- **`start_state`**: A `RobotState` with **`is_diff = True`** and no joint positions set.  
  With `is_diff = True`, MoveIt interprets this as “use the current robot state (e.g. from `/joint_states`) as the start.” So the plan starts from the current configuration.

### Goal constraints

The goal is specified as a **joint-space constraint**:

- **`Constraints`** with a single **`JointConstraint`**:
  - **`joint_name`**: `"shoulder_pan_joint"`  
    First joint of the UR arm (base rotation).
  - **`position`**: `0.0` (radians).  
    Requested joint position.
  - **`tolerance_above`** / **`tolerance_below`**: `0.1` (radians).  
    Acceptable range: `[position - tolerance_below, position + tolerance_above]` → `[-0.1, 0.1]`.
  - **`weight`**: `1.0`  
    Relative weight of this constraint in the optimization.

So the node asks MoveIt to plan a motion to any configuration where `shoulder_pan_joint` is between **-0.1** and **0.1** radians (other joints are free within limits).

### Planning options

- **`goal_msg.planning_options`** is set to a default **`PlanningOptions()`** (no custom options).  
  So MoveIt uses its default behavior (e.g. plan only, or plan-and-execute, depending on how the action server is configured).

---

## Message and action types (reference)

| Type | Package | Description |
|------|---------|-------------|
| `MoveGroup` | `moveit_msgs/action` | Action for requesting (and optionally executing) a motion plan. |
| `MotionPlanRequest` | `moveit_msgs/msg` | Group name, start state, goal constraints, planning time, etc. |
| `PlanningOptions` | `moveit_msgs/msg` | Options controlling planning/execution behavior. |
| `Constraints` | `moveit_msgs/msg` | Container for joint, position, and orientation constraints. |
| `JointConstraint` | `moveit_msgs/msg` | Single joint name, target position, tolerances, weight. |
| `RobotState` | `moveit_msgs/msg` | Full or differential robot state; `is_diff = True` means “use current state.” |

---

## Dependencies

- **rclpy** — ROS 2 Python client library.  
- **moveit_msgs** — MoveIt message and action definitions.  
- **geometry_msgs** — Pulled in via `moveit_msgs` (listed in `package.xml` for consistency).  
- **sensor_msgs** — Imported in the node (e.g. for `JointState`); the node does not currently use it in the sent request.

A running **MoveIt 2** stack (e.g. MoveItPy or `move_group`) that advertises the **MoveGroup** action on **`/move_action`** is required at runtime.

---

## Customization ideas

- **Different group or joints:** Change `req.group_name` and add or modify `JointConstraint` entries (e.g. more joints in `constraint.joint_constraints`).  
- **Different goal:** Use position/orientation constraints (e.g. `PositionConstraint`, `OrientationConstraint`) instead of or in addition to joint constraints.  
- **One-shot vs. repeated goals:** Trigger `send_goal()` from a timer or a service/subscription instead of once in `__init__`.  
- **Feedback and result handling:** Pass callbacks to `send_goal_async()` (e.g. `feedback_callback`, `result_callback`) to react to planning progress and success/failure.  
- **Action name:** If your MoveIt setup uses a different action name, change the second argument to `ActionClient(self, MoveGroup, "<your_action_name>")`.

---

## Summary

The **moveit_publisher** node is a minimal example that connects to the MoveGroup action server at **`/move_action`**, builds a **MotionPlanRequest** for the **`ur_manipulator`** group with a joint-space goal on **`shoulder_pan_joint`** at **0.0 rad** with **±0.1 rad** tolerance, and sends it once at startup. It relies on MoveIt to use the current robot state from **`/joint_states`** as the start and to perform planning (and optionally execution) according to the server configuration.
