
import torch
import numpy as np

# 加载已经训练好的模型文件
model = torch.jit.load('/home/chang/robotics/unitree_mujoco/policy_1.pt')
model.eval()  # 将模型设置为评估模式

print(model)

# 准备输入数据
observation = torch.randn(1, 235)  
  # 将你的观测数据赋值给 observation 变量
observation = observation.unsqueeze(0)  # 为输入数据添加批次维度

# 进行推理
with torch.no_grad():  # 禁用梯度计算以加速推理过程
    action = model(observation)

# 将输出动作转换为 NumPy 数组
action = action.squeeze(0).numpy()

# 输出推理结果
print("Inferred action:", action)
