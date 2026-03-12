# Copyright 2026 EECE5552 Course Project
# Author: abdul rahman
# mohammedabdulr.1@northeastern.edu
print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


class EnvironmentSetup(Node):
    """Publishes table as collision object to MoveIt planning scene."""

    def __init__(self):
        super().__init__('environment_setup')
        self.pub = self.create_publisher(PlanningScene, '/planning_scene', 10)
        self.timer = self.create_timer(1.0, self.publish_scene)
        self.published = False
        self.get_logger().info('EnvironmentSetup node started')

    def publish_scene(self):
        if self.published:
            return

        scene = PlanningScene()
        scene.is_diff = True

        table = CollisionObject()
        table.id = 'work_table'
        table.header.frame_id = 'world'
        table.operation = CollisionObject.ADD

        tabletop = SolidPrimitive()
        tabletop.type = SolidPrimitive.BOX
        tabletop.dimensions = [1.2, 0.8, 0.05]
        tabletop_pose = Pose()
        tabletop_pose.position.x = 0.0
        tabletop_pose.position.y = 0.0
        tabletop_pose.position.z = 0.75
        tabletop_pose.orientation.w = 1.0
        table.primitives.append(tabletop)
        table.primitive_poses.append(tabletop_pose)

        for lx, ly, lz in [
            ( 0.55,  0.35, 0.35),
            ( 0.55, -0.35, 0.35),
            (-0.55,  0.35, 0.35),
            (-0.55, -0.35, 0.35),
        ]:
            leg = SolidPrimitive()
            leg.type = SolidPrimitive.BOX
            leg.dimensions = [0.05, 0.05, 0.7]
            leg_pose = Pose()
            leg_pose.position.x = lx
            leg_pose.position.y = ly
            leg_pose.position.z = lz
            leg_pose.orientation.w = 1.0
            table.primitives.append(leg)
            table.primitive_poses.append(leg_pose)

        scene.world.collision_objects.append(table)
        self.pub.publish(scene)
        self.get_logger().info('Table published to planning scene')
        self.published = True


def main():
    rclpy.init()
    node = EnvironmentSetup()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
