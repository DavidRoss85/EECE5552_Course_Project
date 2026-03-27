
# Object Selection Node

## Overview

The **Object Selection Node** listens for eye gaze coordinates and verbal commands from the user.
When a recognized selection phrase is detected, the node combines the command with the most
recent gaze coordinates and publishes the result to the VLA input topic.

This node acts as the **intent trigger mechanism** for the assistive robotics pipeline.

---

## Responsibilities

The Object Selection Node:

1. Receives gaze coordinates from the eye tracking system.
2. Receives verbal command messages.
3. Checks if the command matches configured selection phrases.
4. Combines the command and gaze location.
5. Publishes the combined message to the VLA module.

---

## Subscribed Topics

| Topic | Message Type | Description |
|------|--------------|-------------|
| `topic_eye_gaze` | `geometry_msgs/Point` | Eye gaze coordinates from the gaze tracking system |
| `text_commands` | `std_msgs/String` | Transcribed speech commands |

---

## Published Topics

| Topic | Message Type | Description |
|------|--------------|-------------|
| `topic_vla_input` | *(Placeholder message)* | Command and gaze coordinates for VLA processing |

---

## Selection Logic

The node waits for phrases defined in the **selection configuration**.

Example phrases:

```
pick that up
pick that up and put it in the box
give me that
```

When a phrase is detected:

```
command_phrase + gaze_coordinates
        ↓
Publish VLA command
```

---

## Example Execution

User interaction:

```
User gaze: (512, 302)
User says: "pick that up"
```

Published message:

```
command: "pick that up"
gaze_x: 512
gaze_y: 302
```

(Current implementation uses placeholder message types.)

---

## Configuration

Selection phrases are defined in:

```
intent_selection.config.selections
```

Example configuration:

```python
VERBAL_COMMANDS = (
    "pick that up",
    "pick that up and put it in the box",
    "give me that"
)
```

---

## Internal State

The node stores:

| Variable | Purpose |
|--------|---------|
| `_current_gaze_coordinates` | Latest gaze position |
| `_last_detected_phrase` | Most recent command phrase |

---

## Message Flow

```
Eye Tracker
      ↓
topic_eye_gaze
      ↓
Object Selection Node
      ↑
Speech Recognition
      ↓
text_commands
      ↓
VLA Input Topic
```

---

## Future Improvements

Several parts of the node currently use placeholder interfaces.

These areas are marked with:

```
#STUB
```

Planned upgrades include:

- Dedicated `VLAInput` message
- Integration with speech recognition module
- Intent confirmation logic
- Multi-command support

---

## Role in System Architecture

```
Eye Tracking
      ↓
Object Selection Node
      ↓
VLA Model
      ↓
Robot Planning
```

The node converts **user intent signals** into structured commands usable by downstream reasoning systems.
