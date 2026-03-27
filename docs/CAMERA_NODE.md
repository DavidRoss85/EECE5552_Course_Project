# Camera Nodes and Launch Files

## Overview

The **perception package** provides a simple camera pipeline for
capturing and publishing camera feeds within the ROS2 system.

This includes:

-   A **Generic Camera Streamer Node** that captures frames from a
    camera and publishes them to a ROS topic.
-   A **Generic Camera Viewer Node** for visualizing image streams.
-   Several **launch files** that simplify starting common camera
    configurations.

These tools are intended primarily for development, testing, and
integration with other modules such as perception and intent selection.

------------------------------------------------------------------------

# Generic Camera Streamer Node

## Purpose

The **Generic Camera Streamer Node** captures frames from a camera using
OpenCV and publishes them to a ROS2 topic as `sensor_msgs/Image`.

This node is designed to support **multiple camera configurations**,
allowing different camera devices and topics to be used depending on the
system setup.

------------------------------------------------------------------------

## Responsibilities

The node performs the following steps:

1.  Opens a camera device using OpenCV.
2.  Captures frames continuously.
3.  Converts frames to ROS `sensor_msgs/Image` messages using
    `cv_bridge`.
4.  Publishes images to a configurable ROS topic.

------------------------------------------------------------------------

## Published Topics

  Topic          Message Type          Description
  -------------- --------------------- ---------------------
  configurable   `sensor_msgs/Image`   Camera image stream

The publish topic is configurable and is typically defined through
configuration presets or launch files.

------------------------------------------------------------------------

## Parameters

  Parameter         Type     Description
  ----------------- -------- --------------------------------------
  `camera_device`   int      OpenCV camera index (0, 1, 2, etc.)
  `publish_topic`   string   ROS topic where images are published
  `frame_rate`      int      Publishing rate of the node timer

### Important Notes

**Camera Device**

The `camera_device` parameter corresponds to the OpenCV device index.

Examples:

  Camera                    Device Index
  ------------------------- --------------
  First camera connected    0
  Second camera connected   1
  Third camera connected    2

If multiple cameras are connected to the system, the device index may
need to be changed.

------------------------------------------------------------------------

**Frame Rate**

The `frame_rate` parameter controls **how often the node publishes
frames**, but it **does not increase the inherent frame rate of the
camera**.

It only controls the timer interval used to publish images.

For example:

-   If the camera runs at **30 FPS**
-   Setting the timer to **60 Hz will not increase the frame rate**

It simply controls how frequently the node publishes frames.

------------------------------------------------------------------------

# Generic Camera Viewer Node

## Purpose

The **Generic Camera Viewer Node** subscribes to an image topic and
displays the incoming frames using OpenCV.

This node is included primarily for **debugging and testing camera
streams**.


------------------------------------------------------------------------

# Launch Files

## Overview

Several launch files are included to simplify starting common camera
configurations.

These launch files are provided as **convenience tools** and are not
strictly required. The nodes can also be started manually.

------------------------------------------------------------------------

## Available Launch Files

  -----------------------------------------------------------------------
  Launch File                         Description
  ----------------------------------- -----------------------------------
  `launch_eye_camera.py`              Streams the camera feed to the eye camera topic

  `launch_full_view_camera.py`        Streams the camera feed to the full view camera topic
  
  `launch_object_view_camera.py`      Streams the camera view to the object view camera topic
  
  -----------------------------------------------------------------------


## Adjustable Parameters

The parameters inside these launch files are intended to be **modified
when necessary**.

Examples include:

### Camera Device

If multiple cameras are connected:

    camera_device = 0

may need to be changed to

    camera_device = 1

or another index depending on the system.

------------------------------------------------------------------------

### Frame Rate

The frame rate can also be adjusted:

    frame_rate = 30

Again, this only affects the **publishing timer** and does not change
the physical camera frame rate.

------------------------------------------------------------------------

## Example Launch

    ros2 launch perception launch_full_view_camera.py

------------------------------------------------------------------------

# Running Nodes Manually

Although launch files are provided for convenience, the nodes can also
be run manually.

Example:

    ros2 run perception generic_camera_streamer

Parameters can be passed using ROS arguments.

Example:

    ros2 run perception generic_camera_streamer --ros-args -p camera_device:=0 -p publish_topic:=/input/camera_feed/rgb/full_view -p frame_rate:=30

------------------------------------------------------------------------

# Testing Camera Feeds

A viewer node is included to help test camera feeds.

Example workflow:

Start the camera streamer:

    ros2 run perception generic_camera_streamer

Start the viewer:

    ros2 run perception generic_camera_viewer --ros-args -p image_topic:=/input/camera_feed/rgb/full_view

This allows verification that the camera feed is publishing correctly.

------------------------------------------------------------------------

# System Role

These camera nodes serve as the **entry point for visual perception** in
the system.

Typical data flow:

Camera Device\
↓\
Camera Streamer Node\
↓\
ROS Image Topic\
↓\
Perception Modules (YOLO detection, etc.)\
↓\
Intent Selection\
↓\
Robot Control

------------------------------------------------------------------------

# Future Improvements

Possible future improvements include:

-   unified multi-camera launch file
-   camera calibration support
-   synchronized multi-camera capture
-   camera health monitoring
