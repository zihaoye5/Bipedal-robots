#!/usr/bin/env python3

# 这个文件用于测试 使用20个历史状态信息重建地形latent的encoder (1d conv encoder) 
# 实现盲走的功能
# 先learn的encoder，然后再用encoder的输出作为actor的输入，actor直接从 teacher 提取
# 测试效果远好于 “直接把历史信息丢进 lstm 然后 lsmt和actor联合训练” 的效果


import time

import mujoco
import mujoco.viewer
import os
import math
from pynput import keyboard
import numpy as np
import torch
import torch.nn as nn

LOAD_ON = False
STUDENT_ON = True
TEACHER_ON = not STUDENT_ON

class Chomp1d(nn.Module):
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous()

class TemporalBlock(nn.Module):
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(self.conv1, self.chomp1, self.relu1, self.dropout1,
                                 self.conv2, self.chomp2, self.relu2, self.dropout2)
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        self.init_weights()

    def init_weights(self):
        self.conv1.weight.data.normal_(0, 0.01)
        self.conv2.weight.data.normal_(0, 0.01)
        if self.downsample is not None:
            self.downsample.weight.data.normal_(0, 0.01)

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TCNEncoder(nn.Module):
    def __init__(self, num_inputs, num_channels, kernel_size=2, dropout=0.2):
        super(TCNEncoder, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = num_inputs if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, stride=1, dilation=dilation_size,
                                     padding=(kernel_size-1) * dilation_size, dropout=dropout)]

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

# 使用 TCN Encoder 来实现适应模块
class AdaptationModule(nn.Module):
    def __init__(self, input_dim=48, embedding_dim=32, z_dim=20, tcn_channels=[32, 32, 32], kernel_size=2, dropout=0.2):
        super(AdaptationModule, self).__init__()
        
        # 输入嵌入MLP
        self.input_embedding = nn.Sequential(
            nn.Linear(input_dim, embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, embedding_dim),
            nn.ReLU()
        )

        # TCN 编码器
        self.tcn_encoder = TCNEncoder(embedding_dim, tcn_channels, kernel_size, dropout)
        
        # Dropout层
        self.dropout = nn.Dropout(0.5)
        
        # 计算卷积后的长度
        conv_output_length = self._get_conv_output_length(20, kernel_size, len(tcn_channels))
        
        # 线性投影层
        self.fc = nn.Linear(tcn_channels[-1] * conv_output_length, z_dim)

    def forward(self, x):
        batch_size, seq_length, input_dim = x.shape
        
        # 将输入嵌入
        x = x.view(-1, input_dim)
        embeddings = self.input_embedding(x)
        
        # 恢复到(batch_size, seq_length, embedding_dim)
        embeddings = embeddings.view(batch_size, seq_length, -1)
        
        # 转置为(batch_size, embedding_dim, seq_length)
        embeddings = embeddings.transpose(1, 2)
        
        # 通过 TCN 编码器
        x = self.tcn_encoder(embeddings)

        # 添加 Dropout 层
        # x = self.dropout(x)
        
        # 展平并通过线性投影层
        x = x.view(batch_size, -1)
        z = self.fc(x)
        
        return z
    
    def _get_conv_output_length(self, input_length, kernel_size, num_layers):
        length = input_length
        for _ in range(num_layers):
            length = (length - 1) // 1 + 1  # 计算经过每层卷积后的长度
        return length

input_dim = 48
seq_length = 20
z_dim = 20


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
        # "/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/data/a1/xml/scene.xml"
    )
else:
    model = mujoco.MjModel.from_xml_path(
        "/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/data/a1/xml/a1_with_load.xml"
    )
data = mujoco.MjData(model)

##########################
# 加载 teacher policy 模型
##########################
device = torch.device("cuda")
policy_model_teacher = torch.jit.load('/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/policy/policy_1.pt')
policy_model_teacher = policy_model_teacher.to(device)
policy_model_teacher.eval()

#################################
# 加载 student policy acotor 模型
################################
policy_model_student = torch.jit.load('/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/model/extracted_actor.pt') 
policy_model_student = policy_model_student.to(device)
policy_model_student.eval()

#########################
# 加载 adapt encoder 模型
##########################
adapt_encoder = AdaptationModule()
adapt_encoder.load_state_dict(torch.load('/home/chang/robotics/quadruped_load_adaption/unitree_mujoco_test/model/tcn_adaptation_encoder_0621_1.pth'))
adapt_encoder = adapt_encoder.to(device)
adapt_encoder.eval()
print(adapt_encoder)

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

student_obs_t = np.zeros(48) # 储存当前时刻的observation
student_obs_t_1 = np.zeros(48) # 储存上一时刻的observation
student_obs_t_2 = np.zeros(48) # 储存上两时刻的observation
student_obs_t_3 = np.zeros(48) # 储存上三时刻的observation
student_obs_t_4 = np.zeros(48) # 储存上四时刻的observation
student_obs_t_5 = np.zeros(48) # 储存上四时刻的observation
student_obs_t_6 = np.zeros(48) # 储存上四时刻的observation
student_obs_t_7 = np.zeros(48)
student_obs_t_8 = np.zeros(48)
student_obs_t_9 = np.zeros(48)
student_obs_t_10 = np.zeros(48)
student_obs_t_11 = np.zeros(48)
student_obs_t_12 = np.zeros(48)
student_obs_t_13 = np.zeros(48)
student_obs_t_14 = np.zeros(48)
student_obs_t_15 = np.zeros(48)
student_obs_t_16 = np.zeros(48)
student_obs_t_17 = np.zeros(48)
student_obs_t_18 = np.zeros(48)
student_obs_t_19 = np.zeros(48)


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
        # 更新encoder的输入
        student_obs_t_19 = student_obs_t_18
        student_obs_t_18 = student_obs_t_17
        student_obs_t_17 = student_obs_t_16
        student_obs_t_16 = student_obs_t_15
        student_obs_t_15 = student_obs_t_14
        student_obs_t_14 = student_obs_t_13
        student_obs_t_13 = student_obs_t_12
        student_obs_t_12 = student_obs_t_11
        student_obs_t_11 = student_obs_t_10
        student_obs_t_10 = student_obs_t_9
        student_obs_t_9 = student_obs_t_8
        student_obs_t_8 = student_obs_t_7
        student_obs_t_7 = student_obs_t_6
        student_obs_t_6 = student_obs_t_5
        student_obs_t_5 = student_obs_t_4
        student_obs_t_4 = student_obs_t_3
        student_obs_t_3 = student_obs_t_2
        student_obs_t_2 = student_obs_t_1
        student_obs_t_1 = student_obs_t
        student_obs_t = observation_student

        encoder_input = np.concatenate([
            student_obs_t_19,
            student_obs_t_18,
            student_obs_t_17,
            student_obs_t_16,
            student_obs_t_15,
            student_obs_t_14,
            student_obs_t_13,
            student_obs_t_12,
            student_obs_t_11,
            student_obs_t_10,
            student_obs_t_9,
            student_obs_t_8,
            student_obs_t_7,
            student_obs_t_6,
            student_obs_t_5,
            student_obs_t_4,
            student_obs_t_3,
            student_obs_t_2,
            student_obs_t_1,
            student_obs_t,
        ]).reshape(1, 20, 48)
        latent = adapt_encoder(torch.from_numpy(encoder_input).float().to(device))
        latent = latent.cpu().detach().numpy().squeeze(0)

        actor_input = np.concatenate([student_obs_t, latent])
        observation_student = actor_input # 为了兼容原来的代码


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
        if time.time() - start < 0.2:
            observation_teacher = torch.from_numpy(observation_teacher).float()
            observation_teacher = observation_teacher.unsqueeze(0)  # 为输入数据添加批次维度
            observation_teacher = observation_teacher.to(device)
            with torch.no_grad():
                action = policy_model_teacher(observation_teacher)
            action = action.cpu().squeeze(0).numpy()
            last_action = action
            print("Teacher.")
        else:
            observation_student = torch.from_numpy(observation_student).float()
            observation_student = observation_student.unsqueeze(0)
            observation_student = observation_student.to(device)
            with torch.no_grad():
                action = policy_model_student(observation_student)
            action = action.cpu().squeeze(0).numpy()
            last_action = action
            # 把action 记录到csv文件中
            # with open('action.csv', 'a') as f:
            #     for i in range(12):
            #         if i == 11:
            #             f.write(str(action[i]*actions_scale))
            #         else:
            #             f.write(str(action[i]*actions_scale) + ',')
            #     f.write('\n')
            

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
            # time.sleep(0.005)

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
