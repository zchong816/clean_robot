import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class TaskManager(Node):
    def __init__(self):
        super().__init__('task_manager')
        self.sub = self.create_subscription(String, '/task_command', self.cb, 10)
        self.pub = self.create_publisher(String, '/task_plan', 10)

    def cb(self, msg):
        self.get_logger().info(f"Task: {msg.data}")
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = TaskManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
