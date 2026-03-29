"""通过 ROS Service 启停 nav2 建图与自主建图（Web/ros2 service call 均适用）。

nav2 建图（等价终端）::
    ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=true slam:=True

- 服务类型: std_srvs/srv/Trigger（请求体为空）
- /start_nav2_slam  — 启动上述 launch（use_sim_time 来自节点参数 use_sim_time；内部为 multiprocessing.Process，子进程内执行 ros2 launch）
- /stop_nav2_slam   — 停止（SIGKILL 子进程 + pkill 清理）

nav2 自主建图（reflex_explore）::
- /start_nav2_reflex_explore — 启动 reflex_explore.launch.py（参数见 reflex_params_file、reflex_map_save_path）
- /stop_nav2_reflex_explore  — 停止

命令行示例::

    ros2 service call /start_nav2_slam std_srvs/srv/Trigger {}
    ros2 service call /stop_nav2_slam std_srvs/srv/Trigger {}
"""

import multiprocessing
import os
import shutil
import signal
import subprocess
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

# 与终端手动执行一致，便于排查；失败时看该文件末尾
_NAV2_SLAM_LOG = '/tmp/clean_robot_nav2_slam.log'


def _build_nav2_slam_cmd(use_sim_time: bool) -> list[str]:
    """与 `ros2 launch turtlebot3_navigation2 navigation2.launch.py ...` 命令行一致。"""
    ros2 = shutil.which('ros2')
    if not ros2:
        raise RuntimeError('未在 PATH 中找到 ros2，请 source 工作空间后再启动 bringup。')
    use_sim = str(use_sim_time).lower()
    return [
        ros2,
        'launch',
        'turtlebot3_navigation2',
        'navigation2.launch.py',
        f'use_sim_time:={use_sim}',
        'slam:=True',
    ]


def _run_nav2_slam_launch(use_sim_time: bool) -> None:
    """子进程入口：阻塞执行与终端一致的 `ros2 launch ... slam:=True`（与 tb3/slam 服务同模式）。"""
    import sys

    try:
        cmd = _build_nav2_slam_cmd(use_sim_time)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    with open(_NAV2_SLAM_LOG, 'a', buffering=1) as logf:
        logf.write(
            f'\n--- nav2_slam (Process) {time.strftime("%Y-%m-%d %H:%M:%S")} ---\n'
        )
        logf.write(f'cmd: {" ".join(cmd)}\n')
        logf.flush()
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=logf,
            stderr=subprocess.STDOUT,
        )
    rc = proc.returncode if proc.returncode is not None else 1
    sys.exit(rc)


def _run_nav2_reflex_explore_launch(
    use_sim_time: bool, params_file: str, map_save_path: str
) -> None:
    """Run nav2_reflex_explore/reflex_explore.launch.py in child process."""
    from ament_index_python.packages import get_package_share_directory
    from launch import LaunchDescription, LaunchService
    from launch.actions import IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource

    pkg_share = get_package_share_directory('nav2_reflex_explore')
    launch_file = os.path.join(pkg_share, 'launch', 'reflex_explore.launch.py')
    use_sim_str = str(use_sim_time).lower()

    launch_rviz = False
    ld = LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_file),
                launch_arguments={
                    'use_sim_time': use_sim_str,
                    'params_file': params_file,
                    # 'map_save_path': map_save_path,
                }.items(),
            )
        ]
    )
    launch_service = LaunchService(argv=[], noninteractive=True)
    launch_service.include_launch_description(ld)
    launch_service.run()


class Nav2SlamLaunchService(Node):
    def __init__(self):
        super().__init__('nav2_slam_launch_service')
        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)
        if not self.has_parameter('reflex_params_file'):
            self.declare_parameter(
                'reflex_params_file',
                './install/nav2_reflex_explore/share/nav2_reflex_explore/params/explorer_params.yaml',
            )
        if not self.has_parameter('reflex_map_save_path'):
            self.declare_parameter('reflex_map_save_path', '/tmp/reflex_map')
        self.srv_start = self.create_service(
            Trigger, 'start_nav2_slam', self.start_nav2_slam_callback
        )
        self.srv_stop = self.create_service(
            Trigger, 'stop_nav2_slam', self.stop_nav2_slam_callback
        )
        self.srv_start_reflex = self.create_service(
            Trigger,
            'start_nav2_reflex_explore',
            self.start_nav2_reflex_explore_callback,
        )
        self.srv_stop_reflex = self.create_service(
            Trigger,
            'stop_nav2_reflex_explore',
            self.stop_nav2_reflex_explore_callback,
        )
        # nav2 建图：multiprocessing.Process 子进程内执行 ros2 launch（与 slam_launch_service 同模式）
        self.nav2_proc: multiprocessing.Process | None = None
        self.reflex_proc: multiprocessing.Process | None = None
        self.get_logger().info(
            'Nav2 SLAM launch service ready: '
            '/start_nav2_slam, /stop_nav2_slam, '
            '/start_nav2_reflex_explore, /stop_nav2_reflex_explore'
        )

    def _pkill_nav2_orphans(self) -> None:
        for pattern in (
            'turtlebot3_navigation2',
            'slam_toolbox',
        ):
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', pattern],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warning(f'pkill -9 nav2 cleanup ({pattern}): {e}')

    def _stop_nav2_process(self) -> None:
        if self.nav2_proc is None:
            return
        if not self.nav2_proc.is_alive():
            self.nav2_proc = None
            self._pkill_nav2_orphans()
            return
        self.get_logger().info(
            'Stopping nav2 slam (SIGKILL Process child + pkill nav2 cleanup)...'
        )
        try:
            os.kill(self.nav2_proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.nav2_proc.join(timeout=15)
        self.nav2_proc = None
        self._pkill_nav2_orphans()

    def _pkill_reflex_orphans(self) -> None:
        for pattern in (
            'reflex_explore.launch.py',
            'nav2_reflex_explore',
            'explorer_params.yaml',
            'explore',
        ):
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', pattern],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warning(f'pkill -9 reflex cleanup ({pattern}): {e}')

    def _stop_reflex_process(self) -> None:
        if self.reflex_proc is None:
            return
        if not self.reflex_proc.is_alive():
            self.reflex_proc = None
            self._pkill_reflex_orphans()
            return
        self.get_logger().info(
            'Stopping nav2 reflex explore launch subprocess with SIGKILL...'
        )
        try:
            os.kill(self.reflex_proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.reflex_proc.join(timeout=15)
        self.reflex_proc = None
        self._pkill_reflex_orphans()

    def start_nav2_slam_callback(self, request, response):
        if self.nav2_proc is not None and self.nav2_proc.is_alive():
            response.success = False
            response.message = 'nav2 slam is already running.'
            return response

        use_sim_time = bool(self.get_parameter('use_sim_time').value)
        try:
            cmd = _build_nav2_slam_cmd(use_sim_time)
        except Exception as e:
            response.success = False
            response.message = str(e)
            self.get_logger().error(response.message)
            return response

        self.get_logger().info(
            f'Starting nav2 slam via multiprocessing.Process: {" ".join(cmd)}'
        )
        try:
            self.nav2_proc = multiprocessing.Process(
                target=_run_nav2_slam_launch,
                args=(use_sim_time,),
                name='nav2_slam_launch',
                daemon=False,
            )
            self.nav2_proc.start()
        except Exception as e:
            self.nav2_proc = None
            response.success = False
            response.message = str(e)
            self.get_logger().error(response.message)
            return response

        self.nav2_proc.join(timeout=2.0)
        if not self.nav2_proc.is_alive():
            code = self.nav2_proc.exitcode
            self.nav2_proc = None
            response.success = False
            response.message = (
                f'nav2 launch 子进程在约 2s 内已退出 (exit {code})。'
                f'请查看: {_NAV2_SLAM_LOG} '
                '（常见：未安装 turtlebot3_navigation2、与 bringup 中 map_server 冲突等）'
            )
            self.get_logger().error(response.message)
            return response

        response.success = True
        response.message = (
            f'nav2 slam 已启动（Process + ros2 launch slam:=True）。日志: {_NAV2_SLAM_LOG}'
        )
        self.get_logger().info(response.message)
        return response

    def stop_nav2_slam_callback(self, request, response):
        if self.nav2_proc is None or not self.nav2_proc.is_alive():
            response.success = False
            response.message = 'nav2 slam is not running.'
            return response

        self.get_logger().info(
            'Stopping nav2 slam (SIGKILL Process child + pkill cleanup)...'
        )
        try:
            self._stop_nav2_process()
            response.success = True
            response.message = 'nav2 slam stopped successfully.'
        except Exception as e:
            response.success = False
            response.message = f'Failed to stop nav2 slam: {e}'
            self.get_logger().error(response.message)

        return response

    def start_nav2_reflex_explore_callback(self, request, response):
        # if self.reflex_proc is not None and self.reflex_proc.is_alive():
        #     response.success = False
        #     response.message = 'nav2 reflex explore is already running.'
        #     return response

        use_sim_time = bool(self.get_parameter('use_sim_time').value)
        params_file = str(self.get_parameter('reflex_params_file').value).strip()
        map_save_path = str(self.get_parameter('reflex_map_save_path').value).strip()
        if not params_file:
            response.success = False
            response.message = 'reflex_params_file is empty.'
            return response
        if not map_save_path:
            response.success = False
            response.message = 'reflex_map_save_path is empty.'
            return response

        self.get_logger().info(
            'Starting nav2 reflex explore via LaunchService in child process '
            f'(use_sim_time:={str(use_sim_time).lower()}, '
            f'params_file:={params_file}, map_save_path:={map_save_path})...'
        )
        try:
            self.reflex_proc = multiprocessing.Process(
                target=_run_nav2_reflex_explore_launch,
                args=(use_sim_time, params_file, map_save_path),
                name='nav2_reflex_explore_launch',
                daemon=False,
            )
            self.reflex_proc.start()
        except Exception as e:
            self.reflex_proc = None
            response.success = False
            response.message = str(e)
            self.get_logger().error(response.message)
            return response

        self.reflex_proc.join(timeout=2.0)
        if not self.reflex_proc.is_alive() and self.reflex_proc.exitcode not in (None, 0):
            code = self.reflex_proc.exitcode
            self.reflex_proc = None
            response.success = False
            response.message = (
                f'nav2 reflex explore launch process exited early with code {code}.'
            )
            self.get_logger().error(response.message)
            return response

        response.success = True
        response.message = (
            'nav2 reflex explore launched '
            '(reflex_explore.launch.py with params_file/map_save_path).'
        )
        self.get_logger().info(response.message)
        return response

    def stop_nav2_reflex_explore_callback(self, request, response):
        if self.reflex_proc is None or not self.reflex_proc.is_alive():
            response.success = False
            response.message = 'nav2 reflex explore is not running.'
            return response

        self.get_logger().info(
            'Stopping nav2 reflex explore (SIGKILL launch child + pkill -9 reflex nodes)...'
        )
        try:
            self._stop_reflex_process()
            response.success = True
            response.message = 'nav2 reflex explore stopped successfully.'
        except Exception as e:
            response.success = False
            response.message = f'Failed to stop nav2 reflex explore: {e}'
            self.get_logger().error(response.message)

        return response


def main(args=None):
    rclpy.init(args=args)
    node = Nav2SlamLaunchService()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
