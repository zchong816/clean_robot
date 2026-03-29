import multiprocessing
import os
import signal
import subprocess

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import Bool
from std_msgs.msg import String
from std_srvs.srv import Trigger


def _sanitize_world_launch_filename(raw: str) -> str:
    """仅允许 turtlebot3_gazebo/share/launch 下的文件名，防路径穿越。"""
    base = os.path.basename((raw or '').strip()) or 'turtlebot3_world.launch.py'
    if not base.endswith('.py'):
        raise ValueError(f'世界 launch 须为 .py 文件: {base!r}')
    return base


def _world_hint_from_launch_basename(launch_basename: str) -> str:
    """TurtleBot3 常见命名：turtlebot3_house.launch.py → turtlebot3_house.world。"""
    base = os.path.basename((launch_basename or '').strip())
    if base.endswith('.launch.py'):
        return base[: -len('.launch.py')] + '.world'
    if base.endswith('.py'):
        return os.path.splitext(base)[0] + '.world'
    return 'turtlebot3_world.world'


def _run_tb3_world_launch(
    use_sim_time: bool, world_launch_file: str, show_ui: bool
) -> None:
    """Runs in a child process main thread — LaunchService forbids non-main threads.

    show_ui False（默认）: 传 gui:=false headless:=true。
    show_ui True: 不传 gui/headless，使用 turtlebot3 launch 默认值（通常带 Gazebo 客户端）。
    """
    from ament_index_python.packages import get_package_share_directory
    from launch import LaunchDescription, LaunchService
    from launch.actions import IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource

    use_sim_str = str(use_sim_time).lower()
    pkg_share = get_package_share_directory('turtlebot3_gazebo')
    launch_file = os.path.join(pkg_share, 'launch', world_launch_file)
    launch_arguments = {'use_sim_time': use_sim_str}
    if not show_ui:
        launch_arguments['gui'] = 'false'
        launch_arguments['headless'] = 'true'
    ld = LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(launch_file),
                launch_arguments=launch_arguments.items(),
            )
        ]
    )
    launch_service = LaunchService(argv=[], noninteractive=True)
    launch_service.include_launch_description(ld)
    launch_service.run()


class TB3LaunchService(Node):
    def __init__(self):
        super().__init__('tb3_launch_service')
        if not self.has_parameter('use_sim_time'):
            self.declare_parameter('use_sim_time', True)
        # 与 `ros2 launch ... gui:=false headless:=true` 一致；可在 bringup 里覆盖
        if not self.has_parameter('tb3_gazebo_gui'):
            self.declare_parameter('tb3_gazebo_gui', False)
        if not self.has_parameter('tb3_gazebo_headless'):
            self.declare_parameter('tb3_gazebo_headless', True)
        if not self.has_parameter('world_launch_file'):
            self.declare_parameter('world_launch_file', 'turtlebot3_world.launch.py')
        # False=无头（gui:=false headless:=true）；True=不传 gui/headless，由 launch 默认（可出 Gazebo UI）
        if not self.has_parameter('tb3_show_ui'):
            self.declare_parameter('tb3_show_ui', False)
        self._world_launch_file = _sanitize_world_launch_filename(
            str(self.get_parameter('world_launch_file').value)
        )
        self._last_launch_basename = self._world_launch_file
        self.sub_world_launch = self.create_subscription(
            String,
            '/tb3_world_launch_file',
            self._on_tb3_world_launch_file,
            10,
        )
        self.sub_show_ui = self.create_subscription(
            Bool,
            '/tb3_show_ui',
            self._on_tb3_show_ui,
            10,
        )
        self.srv_start = self.create_service(Trigger, 'start_tb3_world', self.start_tb3_callback)
        self.srv_stop = self.create_service(Trigger, 'stop_tb3_world', self.stop_tb3_callback)
        self._launch_proc: multiprocessing.Process | None = None
        self.get_logger().info('TB3 Launch Service ready. Waiting for service calls...')

    def _on_tb3_world_launch_file(self, msg: String) -> None:
        raw = (msg.data or '').strip()
        if not raw:
            return
        try:
            self._world_launch_file = _sanitize_world_launch_filename(raw)
        except ValueError as e:
            self.get_logger().warning(f'忽略无效的 /tb3_world_launch_file: {e}')

    def _on_tb3_show_ui(self, msg: Bool) -> None:
        try:
            self.set_parameters(
                [Parameter('tb3_show_ui', Parameter.Type.BOOL, bool(msg.data))]
            )
        except Exception as e:
            self.get_logger().warning(f'同步 /tb3_show_ui 失败: {e}')

    def start_tb3_callback(self, request, response):
        if self._launch_proc is not None and self._launch_proc.is_alive():
            response.success = False
            response.message = 'TurtleBot3 Gazebo World is already running.'
            return response

        use_sim_time = bool(self.get_parameter('use_sim_time').value)
        show_ui = bool(self.get_parameter('tb3_show_ui').value)
        try:
            wf_param = str(self.get_parameter('world_launch_file').value).strip()
            if wf_param:
                world_launch = _sanitize_world_launch_filename(wf_param)
            else:
                world_launch = _sanitize_world_launch_filename(self._world_launch_file)
        except ValueError as e:
            response.success = False
            response.message = str(e)
            self.get_logger().error(response.message)
            return response

        self._last_launch_basename = world_launch
        ui_note = (
            'omit gui/headless (launch defaults)'
            if show_ui
            else 'gui:=false headless:=true'
        )
        self.get_logger().info(
            f'Starting TurtleBot3 Gazebo via LaunchService in child process '
            f'(launch_file:={world_launch}, use_sim_time:={str(use_sim_time).lower()}, '
            f'tb3_show_ui:={show_ui}, {ui_note})...'
        )

        try:
            self._launch_proc = multiprocessing.Process(
                target=_run_tb3_world_launch,
                args=(use_sim_time, world_launch, show_ui),
                name='tb3_world_launch',
                daemon=False,
            )
            self._launch_proc.start()
        except Exception as e:
            self._launch_proc = None
            response.success = False
            response.message = f'Failed to start TurtleBot3 Gazebo World: {e}'
            self.get_logger().error(response.message)
            return response

        # Child can fail quickly (e.g. missing package); wait briefly for immediate exit
        self._launch_proc.join(timeout=2.0)
        if not self._launch_proc.is_alive() and self._launch_proc.exitcode not in (None, 0):
            code = self._launch_proc.exitcode
            self._launch_proc = None
            response.success = False
            response.message = f'Launch process exited early with code {code}.'
            self.get_logger().error(response.message)
            return response

        response.success = True
        response.message = 'TurtleBot3 Gazebo World started successfully (LaunchService in subprocess).'
        self.get_logger().info(response.message)
        return response

    def stop_tb3_callback(self, request, response):
        if self._launch_proc is None or not self._launch_proc.is_alive():
            response.success = False
            response.message = 'TurtleBot3 Gazebo World is not running.'
            return response

        self.get_logger().info(
            'Stopping TurtleBot3 Gazebo World (SIGKILL launch child + pkill -9 gz / launch)...'
        )
        try:
            pid = self._launch_proc.pid
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self._launch_proc.join(timeout=15)
            response.success = True
            response.message = 'TurtleBot3 Gazebo World stopped (SIGKILL + pkill).'
            self.get_logger().info(response.message)
        except Exception as e:
            response.success = False
            response.message = f'Failed to stop TurtleBot3 Gazebo World: {e}'
            self.get_logger().error(response.message)
        finally:
            self._launch_proc = None
            # 优先用本次启动记录的 launch；否则用参数 world_launch_file
            try:
                wf_param = _sanitize_world_launch_filename(
                    str(self.get_parameter('world_launch_file').value)
                )
            except Exception:
                wf_param = 'turtlebot3_world.launch.py'
            launch_pat = self._last_launch_basename or wf_param
            world_hint = _world_hint_from_launch_basename(launch_pat)
            self.get_logger().info(
                f'Stop cleanup: world_launch_file → launch_pat={launch_pat}, world_hint={world_hint}'
            )
            for proc_name in ('gzserver', 'gzclient'):
                try:
                    subprocess.run(
                        ['pkill', '-9', '-f', f'{proc_name}.*{world_hint}'],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception as e:
                    self.get_logger().warning(f'pkill -9 cleanup failed for {proc_name}: {e}')
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', launch_pat],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warning(f'pkill -9 {launch_pat}: {e}')
            # 兜底：清理仍挂着的 turtlebot3 相关进程（launch / gz / 节点名等）
            try:
                subprocess.run(
                    ['pkill', '-9', '-f', 'turtlebot3'],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.get_logger().warning(f'pkill -9 -f turtlebot3 fallback: {e}')

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
