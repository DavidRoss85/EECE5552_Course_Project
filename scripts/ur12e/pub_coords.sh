# change the color to the second argument
ros2 run perception vla_detector --ros-args   -p camera_source:=topic   -p camera_topic:=/cameras/front/image_raw   -p colors:='["red"]' -p display:=true
