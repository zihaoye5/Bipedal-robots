#!/usr/bin/env python3
import time

import mujoco
import mujoco.viewer
import os
import math
from pynput import keyboard
import numpy as np
import torch

LOAD_ON = False
STUDENT_ON = False
TEACHER_ON = not STUDENT_ON



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


# 键盘控制函数
global command


def on_press(key):
    if key == keyboard.Key.up:
        command[0] += command_scale_factor
    elif key == keyboard.Key.down:
        command[0] -= command_scale_factor
    elif key == keyboard.Key.left:
        command[1] -= command_scale_factor
    elif key == keyboard.Key.right:
        command[1] += command_scale_factor
    elif key == keyboard.KeyCode.from_char("l"):
        command[2] -= command_scale_factor
    elif key == keyboard.KeyCode.from_char("r"):
        command[2] += command_scale_factor


##############
# 加载机器人模型
##############
if LOAD_ON == False:
    model = mujoco.MjModel.from_xml_path(
        "/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/data/a1/xml/a1.xml"
    )
else:
    model = mujoco.MjModel.from_xml_path(
        "/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/data/a1/xml/a1_with_load.xml"
    )
data = mujoco.MjData(model)

#################
# 加载 policy 模型
#################
# policy_model = torch.jit.load(
#     "/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/policy/policy_1.pt"
# )
# policy_model = torch.jit.load("/home/chang/robotics/rl_learning/rl_legged_adaption/legged_gym/logs/rough_a1_teacher_student_test/exported/policies/policy_1.pt")
# if not STUDENT_ON:
#     policy_model = torch.jit.load('/home/chang/robotics/rl_learning/rl_legged_adaption/legged_gym/logs/rough_a1/exported/policies/policy_1.pt')
# else:
#     policy_model = torch.jit.load('/home/chang/robotics/rl_learning/rl_legged_adaption/legged_gym/student_training/model/student_policy_traced_model.pt')
# device = torch.device("cuda")
# policy_model = policy_model.to(device)
# policy_model.eval()  # 将模型设置为评估模式

policy_model_teacher = torch.jit.load('/home/chang/robotics/rl_learning/rl_legged_adaption/legged_gym/logs/rough_a1/exported/policies/policy_1.pt')
policy_model_student = torch.jit.load('/home/chang/robotics/rl_learning/rl_legged_adaption/legged_gym/student_training/model/student_policy_traced_model.pt')
device = torch.device("cuda")
policy_model_teacher = policy_model_teacher.to(device)
policy_model_student = policy_model_student.to(device)
policy_model_teacher.eval()
policy_model_student.eval()


###################
# 初始化储存状态的变量
###################
body_pos = np.zeros(3)  # 机器人的位置 在世界坐标系下
body_quat = np.zeros(4)  # 机器人的orientation 在世界坐标系下
body_lin_vel = np.zeros(3)
body_ang_vel = np.zeros(3)
gravity_projection = np.zeros(3)
command = np.zeros(3)
joint_pos = np.zeros(12)
joint_vel = np.zeros(12)
last_action = np.zeros(12)
torques = np.zeros(12)
terrain_height = np.array(
    [
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
        -0.8611,
    ]
)
default_joint_angles = {  # = target angles [rad] when action = 0.0
    "FL_hip_joint": 0.1,  # [rad]
    "FL_thigh_joint": 0.8,  # [rad]
    "FL_calf_joint": -1.5,  # [rad]
    "FR_hip_joint": -0.1,  # [rad]
    "FR_thigh_joint": 0.8,  # [rad]
    "FR_calf_joint": -1.5,  # [rad]
    "RL_hip_joint": 0.1,  # [rad]
    "RL_thigh_joint": 1.0,  # [rad]
    "RL_calf_joint": -1.5,  # [rad]
    "RR_hip_joint": -0.1,  # [rad]
    "RR_thigh_joint": 1.0,  # [rad]
    "RR_calf_joint": -1.5,  # [rad]
}
default_dof_pos = np.array(list(default_joint_angles.values()))

#####################################
# 力矩计算相关增益以及 observation scale
#####################################
p_gains = np.array(
    [20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0, 20.0]
)  # 位置项增益
d_gains = np.array(
    [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
)  # 速度项增益
torque_limits = np.array(
    [20.0, 55.0, 55.0, 20.0, 55.0, 55.0, 20.0, 55.0, 55.0, 20.0, 55.0, 55.0]
)

actions_scale = 0.25
body_lin_vel_scale = 2.0
body_ang_vel_scale = 0.25
command_scale = np.array([2.0, 2.0, 0.25])
joint_pos_scale = 0.05

##############
# 关节状态初始化
##############
data.qpos[7:19] = default_dof_pos

#########################
# 监听键盘输入以发送 command
#########################
command = np.array([0.0, 0.0, 0.0])
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

###########
# 仿真主循环
###########
with mujoco.viewer.launch_passive(model, data) as viewer:
    start = time.time()
    while viewer.is_running() and time.time() - start < 5000:

        ############
        # 更新模型输入
        ############
        body_lin_vel = quaternion_rotate(
            inverse_quaternion(np.array(data.qpos[3:7])), np.array(data.qvel[0:3])
        )  # 机器人的线速度(在机身坐标系)
        body_ang_vel = quaternion_rotate(
            inverse_quaternion(np.array(data.qpos[3:7])), np.array(data.qvel[3:6])
        )  # 机器人的角速度（在机身坐标系）
        gravity_projection = quaternion_rotate(
            inverse_quaternion(np.array(data.qpos[3:7])), np.array([0, 0, -1.0])
        )  # 重力方向投影向量（不是重力向量）
        command_input = command
        joint_pos = np.array(data.qpos[7:19])  # 12个关节的角度(关节位置)
        joint_vel = np.array(data.qvel[6:18])  # 12个关节的角速度(关节速度)

        # 整理 observation 以作为模型输入
        # scale 的值是参考 legged_gym 的代码中的 scale)
        observation_student = np.concatenate([
                    body_lin_vel * body_lin_vel_scale,
                    body_ang_vel * body_ang_vel_scale,
                    gravity_projection,
                    command_input * command_scale,
                    (joint_pos - default_dof_pos),
                    joint_vel * joint_pos_scale,
                    last_action,
                    # terrain_height,
                    ])  # 因为这个里的terrain_height
        observation_teacher = np.concatenate([
                    body_lin_vel * body_lin_vel_scale,
                    body_ang_vel * body_ang_vel_scale,
                    gravity_projection,
                    command_input * command_scale,
                    (joint_pos - default_dof_pos),
                    joint_vel * joint_pos_scale,
                    last_action,
                    terrain_height,
                ])  # 因为这个里的terrain_height
        # 是在isaac gym中采集好的数据，
        # 是已经scaled好的，所以不需要再次scale (5.0)

        #####################################
        # 将 observation 输入模型得到输出 action
        #####################################
        if time.time() - start < 2:
            observation_teacher = torch.from_numpy(observation_teacher).float()
            observation_teacher = observation_teacher.unsqueeze(0)  # 为输入数据添加批次维度
            observation_teacher = observation_teacher.to(device)
            with torch.no_grad():
                action = policy_model_teacher(observation_teacher)
            action = action.cpu().squeeze(0).numpy()
            last_action = action
        else:
            observation_student = torch.from_numpy(observation_student).float()
            observation_student = observation_student.unsqueeze(0)
            observation_student = observation_student.to(device)
            with torch.no_grad():
                action = policy_model_student(observation_student)
            action = action.cpu().squeeze(0).numpy()
            last_action = action
            

        # observation = torch.from_numpy(observation).float()
        # observation = observation.unsqueeze(0)  # 为输入数据添加批次维度
        # observation = observation.to(device)
        # with torch.no_grad():
        #     action = policy_model(observation)
        # action = action.cpu().squeeze(0).numpy()  # 将输出数据转移到 CPU 并转为 numpy
        # last_action = action

        ####################################
        # 将 action 映射为 torque 作为控制输出
        ####################################
        decimation = 1
        for i in range(decimation):
            #########
            # 计算力矩
            #########
            dof_pos = np.array(data.qpos[7:19])
            dof_vel = np.array(data.qvel[6:18])
            torques = (
                p_gains * (action * actions_scale + default_dof_pos - dof_pos)
                - d_gains * dof_vel
            )
            torques = np.clip(torques, -torque_limits, torque_limits)
            data.ctrl[0:12] = torques  # 输入力矩

            #########
            # 执行仿真
            #########
            mujoco.mj_step(model, data)
            time.sleep(0.05)

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

        with viewer.lock():
            viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = int(data.time % 2)
        viewer.sync()
