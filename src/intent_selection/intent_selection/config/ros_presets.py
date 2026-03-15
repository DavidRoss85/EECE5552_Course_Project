# Preset configurations for ROS2

from robot_common.ros_config import(
    TopicKey,
    RosConfig
)

# Simulation (Gazebo) preset:
SIM_CFG = RosConfig()

# Real (Non-simulation) presets:
STD_CFG = RosConfig()