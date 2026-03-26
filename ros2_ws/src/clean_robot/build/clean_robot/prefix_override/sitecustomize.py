import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/ubuntu/workspace/ros2_ws/src/clean_robot/install/clean_robot'
