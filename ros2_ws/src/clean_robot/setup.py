from setuptools import setup
import os
from glob import glob


package_name = 'clean_robot'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    install_requires=['setuptools'],
    
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
    ],


    entry_points={
        'console_scripts': [
            'task_manager = clean_robot.task_manager_node:main',
            'state_machine = clean_robot.state_machine_node:main',
            'battery_manager = clean_robot.battery_manager_node:main',
            'tb3_launch_service = clean_robot.tb3_launch_service:main',
            'slam_launch_service = clean_robot.slam_launch_service:main',
        ],
    },
)
