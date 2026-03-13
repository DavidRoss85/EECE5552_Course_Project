from geometry_msgs.msg import Twist, TwistStamped
import rclpy
from rclpy.node import Node

class TeleopController(Node):
    def __init__(self):
        super().__init__('teleop_controller')

        self.sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cb,
            10
        )

        self.pub = self.create_publisher(
            TwistStamped,
            '/servo_node/delta_twist_cmds',
            10
        )

    def cb(self, msg):
        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = 'tool0'
        out.twist = msg
        self.pub.publish(out)

def main():
    rclpy.init()
    node = TeleopController()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()