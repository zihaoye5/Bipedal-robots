import torch
import torch.nn as nn

class AdaptationModule1DConvEncoderB(nn.Module):
    def __init__(self, input_dim=36, embedding_dim=64, z_dim=10, input_seq_length=20):
        super(AdaptationModule1DConvEncoderB, self).__init__()
        
        # 输入嵌入MLP
        self.input_embedding = nn.Sequential(
            nn.Linear(input_dim, embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, embedding_dim),
            nn.ReLU()
        )

        # Dropout层
        self.dropout = nn.Dropout(0.5)
        
        # 一维卷积层
        self.conv1 = nn.Conv1d(embedding_dim, 128, kernel_size=4, stride=2)
        self.conv2 = nn.Conv1d(128, 256, kernel_size=3, stride=1)
        self.conv3 = nn.Conv1d(256, 512, kernel_size=2, stride=1)
        self.conv4 = nn.Conv1d(512, 512, kernel_size=2, stride=1)
        
        # 计算卷积后的长度
        conv_output_length = self._get_conv_output_length(input_seq_length, [4, 3, 2, 2], [2, 1, 1, 1])
        
        # 线性投影层
        self.fc1 = nn.Linear(512 * conv_output_length, 256)
        self.fc2 = nn.Linear(256, z_dim)

    def forward(self, x):
        batch_size, seq_length, input_dim = x.shape
        
        # 将输入嵌入
        x = x.view(-1, input_dim)
        embeddings = self.input_embedding(x)
        
        # 恢复到(batch_size, seq_length, embedding_dim)
        embeddings = embeddings.view(batch_size, seq_length, -1)
        
        # 转置为(batch_size, embedding_dim, seq_length)
        embeddings = embeddings.transpose(1, 2)
        
        # 通过卷积层
        x = self.conv1(embeddings)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)

        # 添加 Dropout 层
        # x = self.dropout(x)
        
        # 展平并通过线性投影层
        x = x.view(batch_size, -1)
        x = self.fc1(x)
        z = self.fc2(x)
        
        return z
    
    def _get_conv_output_length(self, input_length, kernel_sizes, strides):
        length = input_length
        for k, s in zip(kernel_sizes, strides):
            length = (length - k) // s + 1
        return length

model = AdaptationModule1DConvEncoderB()  # 创建一个AdaptationModule1DConvEncoderB的实例
print(model)