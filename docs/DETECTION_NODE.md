
# Detection Node

## Overview
The **Detection Node** performs real-time object detection using a YOLO model on incoming RGB images.
Detected objects are packaged into ROS messages and published for downstream modules such as
intent selection, visualization, or robot planning.

This node serves as the **perception entry point** for the assistive robotics pipeline.

---

## Responsibilities

The Detection Node:

1. Subscribes to an RGB image stream.
2. Runs YOLO inference on incoming frames.
3. Filters detections based on configured criteria.
4. Packages detection data into `DetectedList` messages.
5. Publishes detection results for other nodes.

Optionally, it can display a debug window showing the annotated detection output.

---

## Subscribed Topics

| Topic | Message Type | Description |
|------|--------------|-------------|
| `topic_object_view_rgb` | `sensor_msgs/Image` | RGB image stream used for object detection |

---

## Published Topics

| Topic | Message Type | Description |
|------|--------------|-------------|
| `detections_topic` | `robot_interfaces/DetectedList` | Contains detected objects and optional annotated images |

---

## Message Format

### DetectedList

```
std_msgs/Header header
sensor_msgs/Image image_raw
sensor_msgs/Image image_annotated
robot_interfaces/DetectedItem[] item_list
```

### DetectedItem

```
int32 index
string name
float32 confidence
int32[4] xyxy
int32[4] xywh
```

---

## Processing Pipeline

```
RGB Image
   ↓
YOLO Model
   ↓
Detection Filtering
   ↓
DetectedItem Objects
   ↓
DetectedList Message
   ↓
Published to detection topic
```

---

## Configuration

The node uses configuration presets from:

```
intent_selection.config.yolo_presets
intent_selection.config.detection_presets
```

Key parameters include:

| Parameter | Description |
|----------|-------------|
| `model` | YOLO model used for inference |
| `confidence_threshold` | Minimum confidence required to accept detections |
| `filter_mode` | Allows or rejects specific classes |
| `target_classes` | Classes allowed when using allow filter |
| `ignore_classes` | Classes rejected when using reject filter |
| `show_feed` | Enables debug display window |

---

## Device Selection

The node supports both CPU and GPU execution.

Device selection logic:

```
CPU_ONLY
THROTTLED
GPU (if available)
```

GPU is automatically selected when available and enabled in configuration.

---

## Debug Visualization

When enabled in the detection configuration:

```
show_feed = True
```

The node will display a window containing:

- Bounding boxes
- Object labels
- Annotated camera feed

---

## Error Handling

Errors during initialization or inference are handled by the internal error handler:

```
_handle_error()
```

This logs structured ROS errors and prevents silent failures.

---

## Role in System Architecture

```
Camera Feed
     ↓
Detection Node
     ↓
DetectedList
     ↓
Intent Selection Node
     ↓
Robot Planning / VLA
```

The Detection Node provides **perception data** used by later modules to interpret user intent.
