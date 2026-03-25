"""Launch the UR ROS2 driver against URSim + MoveIt Servo.

URSim must already be running (e.g. via Docker) before starting this launch.
Default URSim IP is 192.168.56.101.

Usage:
  ros2 launch EECE5552_Course_Project ursim.launch.py
  ros2 launch EECE5552_Course_Project ursim.launch.py robot_ip:=<ip>
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder
from ament_index_python.packages import get_package_share_directory
from launch_param_builder import ParameterBuilder


def generate_launch_description():

    robot_ip_arg = DeclareLaunchArgument(
        'robot_ip',
        default_value='192.168.0.51',
        description='IP address of the URSim instance',
    )
    robot_ip = LaunchConfiguration('robot_ip')

    # UR ROS2 driver connecting to URSim
    ur_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ur_robot_driver'),
                'launch',
                'ur_control.launch.py',
            )
        ),
        launch_arguments={
            'ur_type':           'ur12e',
            'robot_ip':          robot_ip,
            'launch_rviz':       'false',
            'use_mock_hardware': 'false',
            'headless_mode':     'true',
        }.items(),
    )

    moveit_config = (
        MoveItConfigsBuilder('ur', package_name='ur_moveit_config')
        .robot_description_semantic('srdf/ur.srdf.xacro', {'name': 'ur12e'})
        .to_moveit_configs()
    )

    servo_params = {
        "moveit_servo": ParameterBuilder("ur_moveit_config")
        .yaml("config/ur_servo.yaml")
        .to_dict()
    }

    servo_node = Node(
        package="moveit_servo",
        executable="servo_node",
        parameters=[
            servo_params,
            {"update_period": 0.01},
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": False},
        ],
    )

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[
            moveit_config.to_dict(),
            {'use_sim_time': False},
            {'publish_robot_description_semantic': True},
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='log',
        arguments=['-d', os.path.join(
            get_package_share_directory('ur_moveit_config'),
            'config', 'moveit.rviz',
        )],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
            {'use_sim_time': False},
        ],
    )

    # environment_setup_node = Node(
    #     package='robot_control',
    #     executable='environment_setup',
    #     output='screen',
    #     parameters=[{'use_sim_time': False}],
    # )

    # Wait for the driver + controllers to be ready before starting MoveIt
    moveit = TimerAction(
        period=5.0,
        actions=[move_group_node, rviz_node, servo_node],
    )

    # environment_setup = TimerAction(
    #     period=8.0,
    #     actions=[environment_setup_node],
    # )

    home_pose_cmd = (
        'trajectory: {joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, '
        'wrist_1_joint, wrist_2_joint, wrist_3_joint], points: [{positions: [0.0, -1.5707, '
        '1.5707, -1.5707, -1.5707, 0.0], time_from_start: {sec: 3, nanosec: 0}}]}'
    )
    home_pose_action = ExecuteProcess(
        cmd=[
            'ros2', 'action', 'send_goal',
            '/scaled_joint_trajectory_controller/follow_joint_trajectory',
            'control_msgs/action/FollowJointTrajectory',
            home_pose_cmd,
        ],
        output='screen',
        shell=False,
    )
    home_pose = TimerAction(period=10.0, actions=[home_pose_action])

    deactivate_trajectory = ExecuteProcess(
        cmd=['ros2', 'control', 'set_controller_state', 'scaled_joint_trajectory_controller', 'inactive'],
        output='screen',
        shell=False,
    )
    spawn_forward = ExecuteProcess(
        cmd=['ros2', 'run', 'controller_manager', 'spawner', 'forward_position_controller'],
        output='screen',
        shell=False,
    )
    step3_deactivate = TimerAction(period=14.0, actions=[deactivate_trajectory])
    step3_spawn = TimerAction(period=15.0, actions=[spawn_forward])

    set_command_type = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            '/servo_node/switch_command_type',
            'moveit_msgs/srv/ServoCommandType',
            '{command_type: 1}',
        ],
        output='screen',
        shell=False,
    )
    step4 = TimerAction(period=17.0, actions=[set_command_type])

    return LaunchDescription([
        robot_ip_arg,
        ur_driver,
        moveit,
        # environment_setup,
        home_pose,
        step3_deactivate,
        step3_spawn,
        step4,
    ])
