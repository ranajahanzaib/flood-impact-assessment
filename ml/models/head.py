import torch
import torch.nn.functional as F
from torch import nn


class FloodSegmentationHead(nn.Module):
    """
    Lightweight convolutional segmentation head for Earth-Observation foundation models.
    Projects representation features into binary flood probability masks.
    """
    def __init__(self, in_channels: int = 768, hidden_dim: int = 256):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, hidden_dim, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(hidden_dim)
        self.conv2 = nn.Conv2d(hidden_dim, hidden_dim // 2, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(hidden_dim // 2)
        self.conv3 = nn.Conv2d(hidden_dim // 2, 1, kernel_size=1)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor, target_size: tuple[int, int] = None) -> torch.Tensor:
        """
        Input: Tensor of shape (B, C, H, W)
        Output: Tensor of shape (B, 1, target_H, target_W) with logits
        """
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        logits = self.conv3(x)

        if target_size is not None and logits.shape[-2:] != target_size:
            logits = F.interpolate(logits, size=target_size, mode="bilinear", align_corners=False)

        return logits
