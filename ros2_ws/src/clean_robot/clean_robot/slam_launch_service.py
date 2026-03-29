import multiprocessing
import os
import signal
import subprocess

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


def _run_slam_online_async_launch(use_sim_time: bool, slam_params_file: str) -> None:
    """Child process main thread — LaunchService cannot run in a worker thread."""
    from ament_index_python.packages import get_package_share_directory
    from launch import LaunchDescription, LaunchService
    from launch.actions import IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource

    pkg_share = get_package_share_directory('slam_toolbox')
    launch_file = os.path.join(pkg_share, 'launch', 'online_async_launch.py')
    use_sim_str = str(use_sim_time).lower()
    launch_args = {'use_sim_time': use_sim_str}
    if slam_params_file:
        launch_args['slam_params_file'] = slam_params_file
    ld = LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_file),
                launch_arguments=launch_args.items(),
            )
        ]
    )
    launch_service = LaunchService(argv=[], noninteractive=True)
    launch_service.include_launch_description(ld)
    launch_service.run()


class SlamLaunchService(Node):
    def __init__(self):
        super().__init__('slam_launch_service')
        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)
        if not self.has_parameter('slam_params_file'):
            self.declare_parameter('slam_params_file', 'maps/mapper_params.yaml')
        self.srv_start = self.create_service(
            Trigger, 'start_slam_online_async', self.start_slam_callback
        )
        self.srv_stop = self.create_service(
            Trigger, 'stop_slam_online_async', self.stop_slam_callback
        )
        self.slam_proc: multiprocessing.Process | None = None
        self.get_logger().info(
            'SLAM launch service ready: /start_slam_online_async, /stop_slam_online_async'
        )

    def _pkill_slam_toolbox_orphans(self) -> None:
        """Launch 子进程结束后，async_slam_toolbox 等可能仍以独立进程存活，按特征 pkill -9 清理。"""
        for pattern in (
            'online_async_launch.py',
            'async_slam_toolbox',
        ):
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', pattern],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warning(f'pkill -9 slam cleanup ({pattern}): {e}')

    def _stop_slam_process(self) -> None:
        if self.slam_proc is None:
            return
        if not self.slam_proc.is_alive():
            self.slam_proc = None
            self._pkill_slam_toolbox_orphans()
            return
        self.get_logger().info('Stopping SLAM launch subprocess with SIGKILL...')
        try:
            os.kill(self.slam_proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.slam_proc.join(timeout=10)
        self.slam_proc = None
        self._pkill_slam_toolbox_orphans()

    def start_slam_callback(self, request, response):
        if self.slam_proc is not None and self.slam_proc.is_alive():
            response.success = False
            response.message = 'slam_toolbox online_async is already running.'
            return response

        use_sim_time = bool(self.get_parameter('use_sim_time').value)
        raw_params_file = str(self.get_parameter('slam_params_file').value).strip()
        slam_params_file = ''
        if raw_params_file:
            if os.path.isabs(raw_params_file):
                slam_params_file = raw_params_file
            else:
                pkg_share = get_package_share_directory('clean_robot')
                slam_params_file = os.path.normpath(
                    os.path.join(pkg_share, raw_params_file)
                )
        self.get_logger().info(
            f'Starting slam_toolbox online_async via LaunchService in child process '
            f'(use_sim_time:={str(use_sim_time).lower()}, '
            f'slam_params_file:={slam_params_file or "<default>"})...'
        )
        try:
            self.slam_proc = multiprocessing.Process(
                target=_run_slam_online_async_launch,
                args=(use_sim_time, slam_params_file),
                name='slam_online_async_launch',
                daemon=False,
            )
            self.slam_proc.start()
        except Exception as e:
            self.slam_proc = None
            response.success = False
            response.message = str(e)
            self.get_logger().error(response.message)
            return response

        self.slam_proc.join(timeout=2.0)
        if not self.slam_proc.is_alive() and self.slam_proc.exitcode not in (None, 0):
            code = self.slam_proc.exitcode
            self.slam_proc = None
            response.success = False
            response.message = f'slam launch process exited early with code {code}.'
            self.get_logger().error(response.message)
            return response

        response.success = True
        response.message = 'slam_toolbox online_async launched (LaunchService in subprocess).'
        self.get_logger().info(response.message)
        return response

    def stop_slam_callback(self, request, response):
        if self.slam_proc is None or not self.slam_proc.is_alive():
            response.success = False
            response.message = 'slam_toolbox online_async is not running.'
            return response

        self.get_logger().info(
            'Stopping slam_toolbox online_async (SIGKILL launch child + pkill -9 slam)...'
        )
        try:
            self._stop_slam_process()
            response.success = True
            response.message = 'slam_toolbox online_async stopped successfully.'
        except Exception as e:
            response.success = False
            response.message = f'Failed to stop slam_toolbox online_async: {e}'
            self.get_logger().error(response.message)

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
