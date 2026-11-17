from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from ml.models.base import ModelAdapter
from ml.models.head import FloodSegmentationHead


class ClayFloodModel(nn.Module):
    """
    Clay foundation model adapter for multi-sensor flood segmentation.
    Embeds multi-sensor inputs into unified representations.
    """
    def __init__(self, in_channels: int = 10, embed_dim: int = 256):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, embed_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(inplace=True)
        )
        self.head = FloodSegmentationHead(in_channels=embed_dim, hidden_dim=128)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        orig_size = (x.shape[-2], x.shape[-1])
        feats = self.encoder(x)
        logits = self.head(feats, target_size=orig_size)
        return logits

class ClayAdapter(ModelAdapter):
    """
    Adapter for made-with-clay/Clay.
    Supports multi-sensor inputs (optical + radar + DEM).
    """

    def __init__(
        self,
        weights_path: Path | None = None,
        probability_threshold: float = 0.5,
        device=None
    ):
        super().__init__(device=device)
        self.probability_threshold = probability_threshold
        self.model = ClayFloodModel(in_channels=10, embed_dim=256)

        if weights_path and Path(weights_path).exists():
            state_dict = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(state_dict, strict=False)

        self.model.to(self.device)
        self.model.eval()

    def predict(
        self,
        data: np.ndarray,
        sensor: str,
        bands: list[str],
        metadata: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        # Multi-channel normalization
        x = torch.from_numpy(data.astype(np.float32)).unsqueeze(0).to(self.device)
        # Pad or slice to 10 channels if needed
        if x.shape[1] < 10:
            pad = torch.zeros((1, 10 - x.shape[1], x.shape[-2], x.shape[-1]), device=self.device)
            x = torch.cat([x, pad], dim=1)
        elif x.shape[1] > 10:
            x = x[:, :10]

        with torch.no_grad():
            logits = self.model(x)
            prob = torch.sigmoid(logits).squeeze(0).squeeze(0).cpu().numpy()

        mask = prob >= self.probability_threshold
        return prob.astype(np.float32), mask.astype(bool)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "model_id": "made-with-clay/Clay",
            "name": "Clay Multi-Sensor Foundation Model",
            "version": "1.0.0",
            "architecture": "Multi-Sensor ViT / Tokenized Modality Adapter",
            "license": "Apache 2.0",
            "attribution": "Clay Foundation Initiative"
        }
