import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
import subprocess
import os
import signal
from ament_index_python.packages import get_package_share_directory

class TB3LaunchService(Node):
    def __init__(self):
        super().__init__('tb3_launch_service')
        self.srv_start = self.create_service(Trigger, 'start_tb3_world', self.start_tb3_callback)
        self.srv_stop = self.create_service(Trigger, 'stop_tb3_world', self.stop_tb3_callback)
        self.tb3_process = None
        self.get_logger().info('TB3 Launch Service ready. Waiting for service calls...')

    def start_tb3_callback(self, request, response):
        if self.tb3_process is not None and self.tb3_process.poll() is None:
            response.success = False
            response.message = 'TurtleBot3 Gazebo World is already running.'
            return response

        self.get_logger().info('Starting TurtleBot3 Gazebo World...')

        try:
            self.tb3_process = subprocess.Popen(
                ['ros2', 'launch', 'turtlebot3_gazebo', 'turtlebot3_world.launch.py'],
                start_new_session=True
            )
            response.success = True
            response.message = 'TurtleBot3 Gazebo World started successfully.'
            self.get_logger().info(response.message)
        except Exception as e:
            response.success = False
            response.message = f'Failed to start TurtleBot3 Gazebo World: {e}'
            self.get_logger().error(response.message)

        return response

    def stop_tb3_callback(self, request, response):
        if self.tb3_process is None or self.tb3_process.poll() is not None:
            response.success = False
            response.message = 'TurtleBot3 Gazebo World is not running.'
            return response

        self.get_logger().info('Stopping TurtleBot3 Gazebo World...')
        try:
            # 优先结束由本服务启动的 ros2 launch 进程组
            os.killpg(self.tb3_process.pid, signal.SIGTERM)
            self.tb3_process.wait(timeout=10)
            response.success = True
            response.message = 'TurtleBot3 Gazebo World stopped successfully.'
            self.get_logger().info(response.message)
        except subprocess.TimeoutExpired:
            os.killpg(self.tb3_process.pid, signal.SIGKILL)
            response.success = True
            response.message = 'TurtleBot3 Gazebo World force-stopped (killed launch process group).'
            self.get_logger().warning(response.message)
        except Exception as e:
            response.success = False
            response.message = f'Failed to stop TurtleBot3 Gazebo World: {e}'
            self.get_logger().error(response.message)
        finally:
            # 兜底：有时 gzserver/gzclient 会脱离进程组，按 world 特征额外清理
            #（不依赖 psutil；使用 pkill，Ubuntu/多数容器内默认存在）
            world_hint = 'turtlebot3_world.world'
            for proc_name in ('gzserver', 'gzclient'):
                try:
                    subprocess.run(
                        ['pkill', '-TERM', '-f', f'{proc_name}.*{world_hint}'],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass
            self.tb3_process = None

        return response

def main(args=None):
    rclpy.init(args=args)
    node = TB3LaunchService()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()