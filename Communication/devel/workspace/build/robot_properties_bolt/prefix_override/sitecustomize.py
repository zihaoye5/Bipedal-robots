import sys
if sys.prefix == '/home/zihaoye/myenv':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/zihaoye/devel/workspace/install/robot_properties_bolt'
