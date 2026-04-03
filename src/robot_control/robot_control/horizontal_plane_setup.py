import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


class HorizontalPlaneSetup(Node):
    """Publishes a horizontal collision plane at the robot base to MoveIt planning scene.

    A square cutout around the base prevents collisions with the base joint
    while still bounding the gripper and other links.
    """

    PLANE_SIZE = 4.0
    PLANE_THICKNESS = 0.15
    BASE_CUTOUT = 0.8

    def __init__(self):
        super().__init__('horizontal_plane_setup')
        self.pub = self.create_publisher(PlanningScene, '/planning_scene', 10)
        self.timer = self.create_timer(1.0, self.publish_scene)
        self.published = False
        self.get_logger().info('HorizontalPlaneSetup node started')

    def publish_scene(self):
        if self.published:
            return

        scene = PlanningScene()
        scene.is_diff = True

        obj = CollisionObject()
        obj.id = 'ground_plane'
        obj.header.frame_id = 'base_link'
        obj.operation = CollisionObject.ADD

        half = self.PLANE_SIZE / 2.0
        gap = self.BASE_CUTOUT / 2.0
        strip_long = self.PLANE_SIZE
        strip_short = half - gap

        segments = [
            (strip_long, strip_short, 0.0, half - strip_short / 2.0),
            (strip_long, strip_short, 0.0, -(half - strip_short / 2.0)),
            (strip_short, self.BASE_CUTOUT, -(half - strip_short / 2.0), 0.0),
            (strip_short, self.BASE_CUTOUT, half - strip_short / 2.0, 0.0),
        ]

        for sx, sy, cx, cy in segments:
            box = SolidPrimitive()
            box.type = SolidPrimitive.BOX
            box.dimensions = [sx, sy, self.PLANE_THICKNESS]

            pose = Pose()
            pose.position.x = cx
            pose.position.y = cy
            pose.position.z = self.PLANE_THICKNESS / 2.0
            pose.orientation.w = 1.0

            obj.primitives.append(box)
            obj.primitive_poses.append(pose)

        scene.world.collision_objects.append(obj)
        self.pub.publish(scene)
        self.get_logger().info('Ground plane with base cutout published to planning scene')
        self.published = True


def main():
    rclpy.init()
    node = HorizontalPlaneSetup()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
