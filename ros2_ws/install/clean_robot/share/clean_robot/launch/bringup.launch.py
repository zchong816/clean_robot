from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            output='screen',
            parameters=[{'port': 9090}]
        ),

        Node(package='clean_robot', executable='task_manager'),
        Node(package='clean_robot', executable='state_machine'),
        Node(package='clean_robot', executable='battery_manager'),
    ])
