# This node listens for gaze coordinates and text commands.
# When a valid selection phrase is detected, it publishes
# the gaze coordinates and command to the VLA input topic.

# At the moment this module will use pure coordinates for selection, but in the future it may also incorporate object detection results to improve selection accuracy.
# This means that it will need to subscribe to the object detection topic and correlate gaze coordinates with detected objects. For now, it will just pass through the raw gaze coordinates.

# Math / Utility imports
import math
import numpy as np

# ROS2 imports
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import String

# Placeholder interfaces
# These will be replaced later with actual message definitions
from std_msgs.msg import String as VlaInputMessage 

# Configuration imports
from intent_selection.config.selection_presets import DEFAULT_SELECTION_CONFIG
from intent_selection.config.ros_presets import STD_CFG 




class GazeCommandNode(Node):

    def __init__(self):
        super().__init__('gaze_command_node')

        self.get_logger().info('Initializing Gaze Command Node...')


        # Configurations
        self._ros_config = STD_CFG
        self._selection_config = DEFAULT_SELECTION_CONFIG   #STUB


        # Internal state
        self._current_gaze_coordinates = None
        self._last_detected_phrase = None


        # Load parameters
        self._load_parameters()

        try:

            # --------------------------------------------------
            # Subscriber: Eye gaze coordinates
            # --------------------------------------------------

            self._gaze_sub = self.create_subscription(
                Point,
                self._ros_config.topic_eye_gaze,
                self._gaze_callback,
                self._ros_config.max_messages
            )

            self.get_logger().info(
                f'Subscribed to gaze topic: {self._ros_config.topic_eye_gaze.value}'
            )

            # --------------------------------------------------
            # Subscriber: Text commands
            # --------------------------------------------------
            #STUB: This will eventually come from the speech recognition module

            self._command_sub = self.create_subscription(
                String,
                self._ros_config.topic_text_commands,   #STUB
                self._command_callback,
                self._ros_config.max_messages
            )

            self.get_logger().info(
                f'Subscribed to text command topic: {self._ros_config.topic_text_commands.value}'
            )

            # --------------------------------------------------
            # Publisher: VLA input
            # --------------------------------------------------

            self._vla_input_pub = self.create_publisher(
                VlaInputMessage,   #STUB
                self._ros_config.topic_vla_input,
                self._ros_config.max_messages
            )

            self.get_logger().info(
                f'Publisher created on topic: {self._ros_config.topic_vla_input.value}'
            )

            self.get_logger().info('Gaze Command Node initialized and ready.')

        except Exception as e:
            self._handle_error(e, '__init__()', 'Failed to initialize node')
            self.destroy_node()

    # --------------------------------------------------

    def _load_parameters(self):
        """Load external parameters"""
        #STUB: Future parameter loading
        pass

    # --------------------------------------------------

    def _gaze_callback(self, message: Point):
        """
        Stores the most recent gaze coordinates.
        """

        self._current_gaze_coordinates = (message.x, message.y)

    # --------------------------------------------------

    def _command_callback(self, message: String):
        """
        Processes incoming text commands.
        If a valid selection phrase is detected,
        publish gaze coordinates + command to VLA.
        """

        phrase = message.data.lower()
        self._last_detected_phrase = phrase

        # --------------------------------------------------
        # Check if phrase matches configured selection phrases
        # --------------------------------------------------

        if phrase in self._selection_config.text_commands:

            if self._current_gaze_coordinates is None:
                self.get_logger().warn(
                    'Selection phrase detected but gaze coordinates unavailable.'
                )
                return

            self.get_logger().info(
                f'Selection command detected: "{phrase}"'
            )

            self._publish_vla_command(phrase)

    # --------------------------------------------------

    def _publish_vla_command(self, command_phrase: str):
        """
        Publishes gaze coordinates and command
        to the VLA input topic.
        """

        try:

            gaze_x, gaze_y = self._current_gaze_coordinates

            msg = VlaInputMessage()
            # We don't know yet the exact structure of the VLA input message, so we'll just use placeholders for now.
            msg.x = gaze_x   #STUB placeholder
            msg.y = gaze_y   #STUB placeholder
            msg.command = command_phrase   #STUB placeholder

            self._vla_input_pub.publish(msg)

            self.get_logger().info(
                f'Published VLA command | phrase={command_phrase} '
                f'gaze=({gaze_x}, {gaze_y})'
            )

        except Exception as e:
            self._handle_error(e, '_publish_vla_command()', 'Failed to publish VLA input')

    # --------------------------------------------------

    def _handle_error(self, error, function_name, custom_message=''):
        self.get_logger().error(
            f'Error in {function_name}: {str(error)}. {custom_message}'
        )


# --------------------------------------------------


def main(args=None):

    rclpy.init()
    node = GazeCommandNode()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()