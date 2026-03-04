#!/usr/bin/env python3

import time

import mujoco
import mujoco.viewer
import os
import math
import keyboard
import numpy as np
import torch

default_dof_pos = np.array([0.1,0.8,-1.5,
                            -0.1,0.8,-1.5,
                            0.1,1.,-1.5,
                            -0.1,1.,-1.5])



# 加载机器人模型
model = mujoco.MjModel.from_xml_path("/home/chang/robotics/unitree_mujoco/data/a1/urdf/scene.xml")
data = mujoco.MjData(model)

default_joint_angles = { # = target angles [rad] when action = 0.0

    'FR_hip_joint': -0.1 ,  # [rad]
    'FR_thigh_joint': 0.8,     # [rad]
    'FR_calf_joint': -1.5,  # [rad]

    'FL_hip_joint': 0.1,   # [rad]
    'FL_thigh_joint': 0.8,     # [rad]
    'FL_calf_joint': -1.5,   # [rad]

    'RR_hip_joint': -0.1,   # [rad]
    'RR_thigh_joint': 1.,   # [rad]
    'RR_calf_joint': -1.5,    # [rad]

    'RL_hip_joint': 0.1,   # [rad]
    'RL_thigh_joint': 1.,   # [rad]
    'RL_calf_joint': -1.5,    # [rad]

}




with mujoco.viewer.launch_passive(model, data) as viewer:
    start = time.time()
    while viewer.is_running() and time.time() - start < 500:
        mujoco.mj_step(model, data)  # 执行仿真步骤
        # np.set_printoptions(precision=3)

        
        # 暂停 0.5 s
        time.sleep(0.01)

        with viewer.lock():
            viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = int(data.time % 2)
        viewer.sync()




