import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Battery(Node):
    def __init__(self):
        super().__init__('battery')
        self.pub = self.create_publisher(String, '/battery_state', 10)

        self.level = 100
        self.pub.publish(String(data=str(self.level)))
        self.get_logger().info(f"Battery: {self.level}%")

        # Mock 电量：每 2 分钟下降 1%
        self.timer = self.create_timer(30.0, self.tick)
    

    def tick(self):
        if self.level > 0:
            self.level -= 1
        self.pub.publish(String(data=str(self.level)))
        self.get_logger().info(f"Battery: {self.level}%")

def main():
    rclpy.init()
    node = Battery()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
