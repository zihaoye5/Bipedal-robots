import numpy as np
def quat_rotate_inverse(q, v):
    # 假设 q 的形状为 (4,)，v 的形状为 (3,)
    q_w = q[0]
    q_vec = q[1:]
    
    # 计算部分 a
    a = v * (2.0 * q_w ** 2 - 1.0)
    
    # 计算部分 b
    b = np.cross(q_vec, v) * q_w * 2.0
    
    # 计算部分 c
    c = q_vec * (np.dot(q_vec, v) * 2.0)
    
    return a - b + c

# 示例输入
q = np.array([0.9995, -0.0276, 0.0083, -0.0089])
v = np.array([0.0, 0.0, -1.0])

# 调用函数
result = quat_rotate_inverse(q, v)
print(result)

# def inverse_quaternion(q):
#     # 检查输入是否为numpy array
#     if not isinstance(q, np.ndarray):
#         raise TypeError("Input must be a numpy array.")

#     # 检查输入四元数的维度是否正确
#     if q.shape != (4,):
#         raise ValueError("Input must be a 4D vector.")

#     # 计算四元数的模
#     norm = np.linalg.norm(q)

#     # 检查是否为单位四元数,如果不是,则归一化
#     if not np.isclose(norm, 1.0):
#         q = q / norm

#     # 计算共轭四元数
#     q_conj = np.array([q[0], -q[1], -q[2], -q[3]])

#     return q_conj


# def quaternion_rotate(q, v):
#     # 检查输入是否为numpy array
#     if not isinstance(q, np.ndarray) or not isinstance(v, np.ndarray):
#         raise TypeError("Inputs must be numpy arrays.")

#     # 检查输入四元数和向量的维度是否正确
#     if q.shape != (4,) or v.shape != (3,):
#         raise ValueError(
#             "Quaternion must be a 4D vector and input vector must be a 3D vector."
#         )

#     # 归一化四元数
#     q = q / np.linalg.norm(q)

#     # 提取四元数的实部和虚部
#     w, x, y, z = q

#     # 计算旋转后的向量
#     v_rotated = np.zeros(3)
#     v_rotated[0] = (
#         (1 - 2 * y**2 - 2 * z**2) * v[0]
#         + (2 * x * y - 2 * z * w) * v[1]
#         + (2 * x * z + 2 * y * w) * v[2]
#     )
#     v_rotated[1] = (
#         (2 * x * y + 2 * z * w) * v[0]
#         + (1 - 2 * x**2 - 2 * z**2) * v[1]
#         + (2 * y * z - 2 * x * w) * v[2]
#     )
#     v_rotated[2] = (
#         (2 * x * z - 2 * y * w) * v[0]
#         + (2 * y * z + 2 * x * w) * v[1]
#         + (1 - 2 * x**2 - 2 * y**2) * v[2]
#     )

#     return v_rotated

# # 示例输入
# q = np.array([[0.9995,-0.0276,  0.0083, -0.0089]])
# # q = np.array([[-0.0276,  0.0083, -0.0089,  0.9995]])
# v = np.array([[0.0, 0.0, -1.]])

# # 调用函数
result = quat_rotate_inverse(q, v)
print(result)

# print(quaternion_rotate(inverse_quaternion(q[0]), v[0]))

# import torch

# def quat_rotate_inverse(q, v):
#     shape = q.shape
#     q_w = q[:, -1]
#     q_vec = q[:, :3]
#     a = v * (2.0 * q_w ** 2 - 1.0).unsqueeze(-1)
#     b = torch.cross(q_vec, v, dim=-1) * q_w.unsqueeze(-1) * 2.0
#     c = q_vec * \
#         torch.bmm(q_vec.view(shape[0], 1, 3), v.view(
#             shape[0], 3, 1)).squeeze(-1) * 2.0
#     return a - b + c

# q = torch.tensor([[-0.0276,  0.0083, -0.0089,  0.9995]])
# v = torch.tensor([[0.,  0., -1.]])

# # q=torch.tensor([[-0.0276,  0.0083, -0.0089,  0.9995]], device='cuda:0').detach().cpu().numpy()
# # v=torch.tensor([[ 0.,  0., -1.]], device='cuda:0').detach().cpu().numpy()   
# # tensor([[ 0.0161,  0.0552, -0.9983]], device='cuda:0')

# result = quat_rotate_inverse(q, v)
# print(result)