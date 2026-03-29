import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _resolve_map_yaml_file(context):
    raw = LaunchConfiguration('map_yaml_file').perform(context)
    # 保险策略：绝对路径直接用；相对路径固定相对 clean_robot 包 share 目录
    if os.path.isabs(raw):
        resolved = raw
    else:
        pkg_share = get_package_share_directory('clean_robot')
        resolved = os.path.normpath(os.path.join(pkg_share, raw))
    return [SetLaunchConfiguration('resolved_map_yaml_file', resolved)]

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    resolved_map_yaml_file = LaunchConfiguration('resolved_map_yaml_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock if true'
        ),
        DeclareLaunchArgument(
            'map_yaml_file',
            default_value='maps/empty.yaml',
            description='Map yaml path; relative path is resolved from clean_robot share directory'
        ),
        OpaqueFunction(function=_resolve_map_yaml_file),

        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            output='screen',
            parameters=[{'port': 9090}]
        ),

        Node(
            package='rosapi',
            executable='rosapi_node',
            name='rosapi',
            output='screen'
        ),

        Node(
            package='clean_robot',
            executable='task_manager',
            parameters=[{'use_sim_time': use_sim_time}]
        ),
        Node(
            package='clean_robot',
            executable='state_machine',
            parameters=[{'use_sim_time': use_sim_time}]
        ),
        Node(
            package='clean_robot',
            executable='battery_manager',
            parameters=[{'use_sim_time': use_sim_time}]
        ),
        Node(
            package='clean_robot',
            executable='tb3_launch_service',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}]
        ),
        Node(
            package='clean_robot',
            executable='slam_launch_service',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}]
        ),
        Node(
            package='clean_robot',
            executable='nav2_slam_launch_service',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}]
        ),
        Node(
            package='nav2_map_server',
            executable='map_server',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'yaml_filename': resolved_map_yaml_file,
                'topic_name': 'map_load',
            }]
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map_server',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': ['map_server'],
            }]
        ),
    ])
