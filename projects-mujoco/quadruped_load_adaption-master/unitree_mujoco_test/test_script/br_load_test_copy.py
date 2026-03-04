#!/usr/bin/env python3
import time

import mujoco
import mujoco.viewer
import os
import math
from pynput import keyboard
import numpy as np
import torch
import pygame
import threading
import rospy
from sensor_msgs.msg import Imu



LOAD_ON = False

def inverse_quaternion(q):
    # 检查输入是否为numpy array
    if not isinstance(q, np.ndarray):
        raise TypeError("Input must be a numpy array.")

    # 检查输入四元数的维度是否正确
    if q.shape != (4,):
        raise ValueError("Input must be a 4D vector.")

    # 计算四元数的模
    norm = np.linalg.norm(q)

    # 检查是否为单位四元数,如果不是,则归一化
    if not np.isclose(norm, 1.0):
        q = q / norm

    # 计算共轭四元数
    q_conj = np.array([q[0], -q[1], -q[2], -q[3]])

    return q_conj


def quaternion_rotate(q, v):
    # 检查输入是否为numpy array
    if not isinstance(q, np.ndarray) or not isinstance(v, np.ndarray):
        raise TypeError("Inputs must be numpy arrays.")

    # 检查输入四元数和向量的维度是否正确
    if q.shape != (4,) or v.shape != (3,):
        raise ValueError(
            "Quaternion must be a 4D vector and input vector must be a 3D vector."
        )

    # 归一化四元数
    q = q / np.linalg.norm(q)

    # 提取四元数的实部和虚部
    w, x, y, z = q

    # 计算旋转后的向量
    v_rotated = np.zeros(3)
    v_rotated[0] = (
        (1 - 2 * y**2 - 2 * z**2) * v[0]
        + (2 * x * y - 2 * z * w) * v[1]
        + (2 * x * z + 2 * y * w) * v[2]
    )
    v_rotated[1] = (
        (2 * x * y + 2 * z * w) * v[0]
        + (1 - 2 * x**2 - 2 * z**2) * v[1]
        + (2 * y * z - 2 * x * w) * v[2]
    )
    v_rotated[2] = (
        (2 * x * z - 2 * y * w) * v[0]
        + (2 * y * z + 2 * x * w) * v[1]
        + (1 - 2 * x**2 - 2 * y**2) * v[2]
    )

    return v_rotated

##控制方式：键盘控制、手柄控制
############
#1.键盘控制函数
############
# global command

def on_press(key):
    if key == keyboard.Key.up:
        command[0] = min(command[0] + acceleration[0], max_velocity[0])
    elif key == keyboard.Key.down:
        command[0] = max(command[0] - acceleration[0], -max_velocity[0])
    elif key == keyboard.Key.left:
        # command[1] = max(command[1] - acceleration[1], -max_velocity[1])
        command[1] = min(command[1] + acceleration[1], max_velocity[1])
    elif key == keyboard.Key.right:
        # command[1] = min(command[1] + acceleration[1], max_velocity[1])
        command[1] = max(command[1] - acceleration[1], -max_velocity[1])
    elif key == keyboard.KeyCode.from_char("l"):
        # command[2] = max(command[2] - acceleration[2], -max_velocity[2])
        command[2] = min(command[2] + acceleration[2], max_velocity[2])
    elif key == keyboard.KeyCode.from_char("r"):
        # command[2] = min(command[2] + acceleration[2], max_velocity[2])
        command[2] = max(command[2] - acceleration[2], -max_velocity[2])


def on_release(key):
    if key in [keyboard.Key.up, keyboard.Key.down]:
        command[0] = 0
    elif key in [keyboard.Key.left, keyboard.Key.right]:
        command[1] = 0
    elif key in [keyboard.KeyCode.from_char("l"), keyboard.KeyCode.from_char("r")]:
        command[2] = 0


################
#2. 创建手柄控制模块
################
# 新增: 全局变量来存储手柄数据 
# joystick_data = {
#     "lx": 0.0,  # 左摇杆 X
#     "ly": 0.0,  # 左摇杆 Y
#     "rx": 0.0,  # 右摇杆 X
#     "ry": 0.0,  # 右摇杆 Y
#     "a": 0,     # A 按钮
#     "b": 0,     # B 按钮
#     "x": 0,     # X 按钮
#     "y": 0,     # Y 按钮
# }
# #初始化
# pygame.init()
# joystick = pygame.joystick.Joystick(0)
# joystick.init()
# def get_joystick_input():
#     pygame.event.pump()
#     # 读取摇杆
#     lx = joystick.get_axis(0)  # 左摇杆 X
#     ly = joystick.get_axis(1)  # 左摇杆 Y
#     rx = joystick.get_axis(3)  # 右摇杆 X
#     ry = joystick.get_axis(4)  # 右摇杆 Y

#     button_a = joystick.get_button(0)  # A
#     button_b = joystick.get_button(1)  # B
#     button_x = joystick.get_button(2)  # X
#     button_y = joystick.get_button(3)  # Y
#     return lx, ly, rx, ry, button_a, button_b, button_x, button_y

# # === 修改: 用线程循环读取手柄数据并写入全局变量 ===
# def joystick_thread():
#     global joystick_data
#     while True:
#         lx, ly, rx, ry, a, b, x, y = get_joystick_input()
#         joystick_data["lx"] = lx
#         joystick_data["ly"] = ly
#         joystick_data["rx"] = rx
#         joystick_data["ry"] = ry
#         joystick_data["a"]  = a
#         joystick_data["b"]  = b
#         joystick_data["x"]  = x
#         joystick_data["y"]  = y

#         time.sleep(0.01)

# # 启动手柄输入线程
# threading.Thread(target=joystick_thread, daemon=True).start()


##############
# 加载机器人模型
##############
if LOAD_ON == False:
    model = mujoco.MjModel.from_xml_path(
        "/home/zihaoye/projects-mujoco/quadruped_load_adaption-master/unitree_mujoco_test/data/bipedrobot/xml/bipedrobot.xml"
    )
else:
    model = mujoco.MjModel.from_xml_path(
        "/home/zihaoye/projects-mujoco/quadruped_load_adaption-master/unitree_mujoco_test/data/bipedrobot/xml/bipedrobot.xml"
    )
# MjData 对象。这是 MuJoCo 仿真中的关键对象，它包含了仿真中的所有动态数据，例如机器人在仿真过程中的状态、传感器数据等
data = mujoco.MjData(model)#通信

#################
# 加载 policy 模型
#################
policy_model = torch.jit.load(
    "/home/zihaoye/projects-mujoco/quadruped_load_adaption-master/unitree_mujoco_test/policy/policy_br.pt"
)

device = torch.device("cuda")
policy_model = policy_model.to(device)  # 将模型的参数和缓存移动到指定的设备上（GPU）
policy_model.eval()  # 将模型设置为评估模式

###################
# 初始化储存状态的变量
###################
body_pos = np.zeros(3)  # 机器人的位置 在世界坐标系下
body_quat = np.zeros(4)  # 机器人的orientation 在世界坐标系下
body_lin_vel = np.zeros(3)
body_ang_vel = np.zeros(3)
gravity_projection = np.zeros(3)
command = np.zeros(3)
joint_pos = np.zeros(6)
joint_vel = np.zeros(6)
last_action = np.zeros(6)
torques = np.zeros(6)
terrain_height = np.array(
    [
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
        -0.35,
    ]
)
default_joint_angles = {  # = target angles [rad] when action = 0.0
    "FL_HAA": -0.081,
    'FL_HFE': -0.156,
    'FL_KFE': 0.456,

    'FR_HAA': 0.049,
    'FR_HFE': -0.294,
    'FR_KFE': 0.486,
}
default_dof_pos = np.array(list(default_joint_angles.values()))

#####################################
# 力矩计算相关增益以及 observation scale
#####################################
p_gains = np.array(
    [3., 3., 3., 3., 3., 3.]
)  # 位置项增益
d_gains = np.array(
    [0.0500, 0.0500, 0.0500, 0.0500, 0.0500, 0.0500]
)  # 速度项增益
torque_limits = np.array(
    [2.7000, 2.7000, 2.7000, 2.7000, 2.7000, 2.7000]  # Need further revision
)

actions_scale = 0.5  # 缩放来自策略网络或控制器的输出动作
body_lin_vel_scale = 2.0
body_ang_vel_scale = 0.25
command_scale = np.array([2.0, 2.0, 0.25])
joint_pos_scale = 0.05

##############
# 关节状态初始化
##############
data.qpos[7:13] = default_dof_pos

#########################
# 监听键盘输入以发送 command
#########################
command = np.array([0.0, 0.0, 0.0])

# === 全局变量：保存最新的 IMU 数据 ===
imu_orientation = np.array([1.0, 0.0, 0.0, 0.0])  # w, x, y, z
imu_ang_vel = np.zeros(3)
imu_lin_acc = np.zeros(3)
imu_data_lock = threading.Lock()
imu_ready = False


#这个函数在收到 IMU 数据时会自动被调用，并更新你仿真中要用到的本体状态信息。
# def imu_callback(msg):
#     global imu_orientation, imu_ang_vel, imu_lin_acc, imu_ready
#     with imu_data_lock:
#         imu_orientation = np.array([
#             msg.orientation.w,
#             msg.orientation.x,
#             msg.orientation.y,
#             msg.orientation.z
#         ])
#         imu_ang_vel = np.array([
#             msg.angular_velocity.x,
#             msg.angular_velocity.y,
#             msg.angular_velocity.z
#         ])
#         imu_lin_acc = np.array([
#             msg.linear_acceleration.x,
#             msg.linear_acceleration.y,
#             msg.linear_acceleration.z
#         ])
#         imu_ready = True

prev_command = np.array([0.0, 0.0, 0.0])
print(
    "Use arrow keys to move the robot.\n",
    "'l': turn left\n",
    "'r': turn left\n",
    "UP: move forward,\n",
    "DOWN: move backward,\n",
    "LEFT: move left,\n" "RIGHT: move right.\n",
)
command_scale_factor = 0.1
listener = keyboard.Listener(on_press=on_press)
listener.start()


command = np.array([0.0, 0.0, 0.0])
acceleration = np.array([0.05, 0.05, 0.025])
max_velocity = np.array([2.0, 2.0, 1.0])
prev_command = np.array([0.0, 0.0, 0.0])

#跳跃蹲下
jump_offset = np.array([ 0.5,  0.0, -0.5,  0.5,  0.0, -0.5]) 
crouch_offset = np.array([-0.3,  0.0,  0.3, -0.3,  0.0,  0.3])
print(
    "Use arrow keys to move the robot.\n",
    "'l': turn left\n",
    "'r': turn right\n",
    "UP: move forward,\n",
    "DOWN: move backward,\n",
    "LEFT: move left,\n",
    "RIGHT: move right.\n",
)

command_scale_factor = 0.1
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# # === 初始化 ROS 节点与订阅 IMU 数据 ===
# rospy.init_node('imu_mujoco_bridge', anonymous=True)
# rospy.Subscriber('/imu/data', Imu, imu_callback)

# # === 等待 imu_ready 为 True，确保已经收到了 IMU 数据 ===
# print("等待 IMU 数据准备...")
# while not imu_ready and not rospy.is_shutdown():
#     rospy.sleep(0.1)
# print("IMU 数据已准备，开始仿真。")

###########
# 仿真主循环
###########
with mujoco.viewer.launch_passive(model, data) as viewer:
    start = time.time()
    while viewer.is_running() and time.time() - start < 5000:

        # 新增: 用左摇杆 & 右摇杆更新 command
        # 通常 axis = -1 时为向上/左，+1 为向下/右，
        # 如果你想前推摇杆表示正向速度，可以对 ly 取负号
        # ly = joystick_data["ly"]  # 向上推时 ly ~ -1
        # lx = joystick_data["lx"]
        # rx = joystick_data["rx"]  # 右摇杆 X

        # # 例如：command[0] 表示前进/后退，command[1] 表示左/右平移，command[2] 表示转向
        # # 注意：具体映射可根据需求自行调整
        # command[0] = -ly * 0.5  # 前进后退（-ly 是为了让向上推摇杆 = 正前进）
        # command[1] = -lx * 0.5   # 左右平移
        # command[2] = rx * 0.5   # 左右转向（yaw），系数可调大/小

        # # === 示例: 检测 A/B/X/Y 按钮并打印
        # if joystick_data["a"] == 1:
        #     # A 按下 => 跳跃
        #     offset = jump_offset
        # elif joystick_data["b"] == 1:
        #     # B 按下 => 蹲下
        #     offset = crouch_offset
        # else:
        #     # 都没按 => 不偏移
        #     offset = np.zeros(6)

        ############
        # 更新模型输入
        ############

        # with imu_data_lock:
        #     body_quat = imu_orientation.copy()
        #     body_ang_vel = imu_ang_vel.copy()
        #     gravity_projection = quaternion_rotate(
        #         inverse_quaternion(body_quat), np.array([0, 0, -1.0])
        #     )
        # body_lin_vel = quaternion_rotate(
        #     inverse_quaternion(np.array(data.qpos[3:7])), np.array(data.qvel[0:3])
        # )  # 机器人的线速度(在机身坐标系)


        body_lin_vel = quaternion_rotate(
            inverse_quaternion(np.array(data.qpos[3:7])), np.array(data.qvel[0:3])
        )  # 机器人的线速度(在机身坐标系)
        body_ang_vel = quaternion_rotate(
            inverse_quaternion(np.array(data.qpos[3:7])), np.array(data.qvel[3:6])
        )  # 机difficulty器人的角速度（在机身坐标系）
        gravity_projection = quaternion_rotate(
            inverse_quaternion(np.array(data.qpos[3:7])), np.array([0, 0, -1.0])
        )  # 重力方向投影向量（不是重力向量）
        command_input = command
        joint_pos = np.array(data.qpos[7:13])  # 6个关节的角度(关节位置)
        joint_vel = np.array(data.qvel[6:12])  # 6个关节的角速度(关节速度)

        # 整理 observation 以作为模型输入
        # scale 的值是参考 legged_gym 的代码中的 scale)
        observation = np.concatenate(
            [
                body_lin_vel * body_lin_vel_scale,
                body_ang_vel * body_ang_vel_scale,
                gravity_projection,
                command_input * command_scale,
                (joint_pos - default_dof_pos),
                joint_vel * joint_pos_scale,
                last_action,
                terrain_height,
            ]
        )  # 因为这个里的terrain_height
        # 是在isaac gym中采集好的数据，
        # 是已经scaled好的，所以不需要再次scale (5.0)

        #####################################
        # 将 observation 输入模型得到输出 action
        #####################################
        observation = torch.from_numpy(observation).float()
        observation = observation.unsqueeze(0)  # 为输入数据添加批次维度
        observation = observation.to(device)
        with torch.no_grad():
            action = policy_model(observation)
        action = action.cpu().squeeze(0).numpy()  # 将输出数据转移到 CPU 并转为 numpy
        last_action = action

        ####################################
        # 将 action 映射为 torque 作为控制输出
        ####################################
        decimation = 1
        for i in range(decimation):
            #########
            # 计算力矩
            #########
            dof_pos = np.array(data.qpos[7:13])
            dof_vel = np.array(data.qvel[6:12])
            # torques = (
            #     p_gains * ((action+offset) * actions_scale + default_dof_pos - dof_pos)
            #     - d_gains * dof_vel
            # )
            torques = (
                p_gains * ((action) * actions_scale + default_dof_pos - dof_pos)
                - d_gains * dof_vel
            )
            torques = np.clip(torques, -torque_limits, torque_limits)
            data.ctrl[0:6] = torques  # 输入力矩 通信输入
            #########
            # 执行仿真
            #########
            mujoco.mj_step(model, data) #根据当前的模型 (model) 和仿真状态 (data)，通过物理引擎计算下一时刻系统的状态 通信输出
            time.sleep(0.005)

        ###################
        # 实时输出command命令
        ###################
        if not np.array_equal(command, prev_command):
            print(
                "Use arrow keys to move the robot.\n",
                "'l': turn left\n",
                "'r': turn left\n",
                "UP: move forward,\n",
                "DOWN: move backward,\n",
                "LEFT: move left,\n" "RIGHT: move right.\n",
            )
            print(
                "x_velocity: {:.2f},\ny_velocity: {:.2f},\nangular_velocity: {:.2f}\n".format(
                    command[0], command[1], command[2]
                )
            )
            prev_command = command.copy()

        # if not np.array_equal(command, prev_command):
        #     print(f"command = {command}")
        #     prev_command = command.copy()
        


        with viewer.lock():
            viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = int(data.time % 2)
        viewer.sync()
