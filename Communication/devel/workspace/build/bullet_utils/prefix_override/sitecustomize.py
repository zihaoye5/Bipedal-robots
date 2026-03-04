import sys
if sys.prefix == '/home/zihaoye/myenv':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/zihaoye/devel/workspace/install/bullet_utils'
