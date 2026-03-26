import subprocess
import signal

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class SlamLaunchService(Node):
    def __init__(self):
        super().__init__('slam_launch_service')
        self.srv_start = self.create_service(
            Trigger, 'start_slam_online_async', self.start_slam_callback
        )
        self.srv_stop = self.create_service(
            Trigger, 'stop_slam_online_async', self.stop_slam_callback
        )
        self.slam_process = None
        self.get_logger().info(
            'SLAM launch service ready: /start_slam_online_async, /stop_slam_online_async'
        )

    def start_slam_callback(self, request, response):
        if self.slam_process is not None and self.slam_process.poll() is None:
            response.success = False
            response.message = 'slam_toolbox online_async is already running.'
            return response

        self.get_logger().info('Starting slam_toolbox online_async (use_sim_time:=true)...')
        try:
            self.slam_process = subprocess.Popen(
                [
                    'ros2',
                    'launch',
                    'slam_toolbox',
                    'online_async_launch.py',
                    'use_sim_time:=true',
                ],
                start_new_session=True,
            )
            response.success = True
            response.message = 'slam_toolbox online_async launched.'
        except Exception as e:
            response.success = False
            response.message = str(e)
            self.get_logger().error(response.message)
        return response

    def stop_slam_callback(self, request, response):
        if self.slam_process is None or self.slam_process.poll() is not None:
            response.success = False
            response.message = 'slam_toolbox online_async is not running.'
            return response

        self.get_logger().info('Stopping slam_toolbox online_async...')
        try:
            # start_new_session=True 时，pid 即进程组 ID
            self.slam_process.send_signal(signal.SIGINT)
            self.slam_process.wait(timeout=10)
            response.success = True
            response.message = 'slam_toolbox online_async stopped successfully.'
        except subprocess.TimeoutExpired:
            self.slam_process.terminate()
            try:
                self.slam_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.slam_process.kill()
                self.slam_process.wait()
            response.success = True
            response.message = 'slam_toolbox online_async force-stopped.'
        except Exception as e:
            response.success = False
            response.message = f'Failed to stop slam_toolbox online_async: {e}'
            self.get_logger().error(response.message)
        finally:
            self.slam_process = None

        return response


def main(args=None):
    rclpy.init(args=args)
    node = SlamLaunchService()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
