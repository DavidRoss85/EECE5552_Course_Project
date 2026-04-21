# Main entry: UR12e driver + MoveIt + Servo + joystick teleop (see launch/ursim_with_joy_teleop.launch.py).
# From repo root after sourcing install/setup.bash; set robot_ip to your controller.
ros2 launch launch/ursim_with_joy_teleop.launch.py robot_ip:=10.18.1.106