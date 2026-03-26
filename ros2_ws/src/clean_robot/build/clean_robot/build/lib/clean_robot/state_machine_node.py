import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class StateMachine(Node):
    def __init__(self):
        super().__init__('state_machine')
        self.state = "IDLE"
        self.sub = self.create_subscription(String, '/task_plan', self.cb, 10)
        self.pub = self.create_publisher(String, '/robot_state', 10)

    def cb(self, msg):
        data = json.loads(msg.data)
        t = data.get("type")

        if t == "start_cleaning":
            self.state = "CLEANING"
        elif t == "start_mapping":
            self.state = "MAPPING"

        self.pub.publish(String(data=self.state))
        self.get_logger().info(f"State: {self.state}")

def main():
    rclpy.init()
    node = StateMachine()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
