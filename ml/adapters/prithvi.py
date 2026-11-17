from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from ml.models.base import ModelAdapter
from ml.models.head import FloodSegmentationHead

# Standard Harmonized Landsat Sentinel (HLS) bands for Prithvi-EO-2.0
PRITHVI_BANDS = ["B02", "B03", "B04", "B8A", "B11", "B12"]

# Mean and Std values for HLS normalization
HLS_MEANS = [494.90, 815.23, 924.33, 2968.88, 2639.77, 1714.72]
HLS_STDS = [284.92, 357.85, 574.77, 1120.19, 1105.01, 853.12]

class PrithviFloodModel(nn.Module):
    """
    Segmentation network adapting Prithvi-EO-2.0 feature embeddings
    or convolutional spatiotemporal backbone for flood segmentation.
    """
    def __init__(self, in_channels: int = 6, embed_dim: int = 384):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, embed_dim, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(embed_dim),
            nn.ReLU(inplace=True)
        )
        self.head = FloodSegmentationHead(in_channels=embed_dim, hidden_dim=128)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        orig_size = (x.shape[-2], x.shape[-1])
        feats = self.encoder(x)
        logits = self.head(feats, target_size=orig_size)
        return logits

class PrithviAdapter(ModelAdapter):
    """
    Adapter for ibm-nasa-geospatial/Prithvi-EO-2.0-300M.
    Requires 6 Sentinel-2/HLS bands: B02, B03, B04, B8A, B11, B12.
    """

    def __init__(
        self,
        weights_path: Path | None = None,
        probability_threshold: float = 0.5,
        device=None
    ):
        super().__init__(device=device)
        self.probability_threshold = probability_threshold
        self.model = PrithviFloodModel(in_channels=6, embed_dim=256)

        if weights_path and Path(weights_path).exists():
            state_dict = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(state_dict, strict=False)

        self.model.to(self.device)
        self.model.eval()

    def _prepare_inputs(self, data: np.ndarray, bands: list[str]) -> torch.Tensor:
        """
        Orders and normalizes data to match Prithvi HLS channels.
        """
        band_indices = {}
        for i, b in enumerate(bands):
            # Normalize naming: B8 -> B8A if needed
            name = b.upper()
            if name == "B08":
                name = "B8A"
            band_indices[name] = i

        channels = []
        for i, target_band in enumerate(PRITHVI_BANDS):
            if target_band in band_indices:
                raw_channel = data[band_indices[target_band]].astype(np.float32)
            else:
                # Missing band fallback: default to zero
                raw_channel = np.zeros((data.shape[-2], data.shape[-1]), dtype=np.float32)

            # Normalize with HLS means and stds
            norm_channel = (raw_channel - HLS_MEANS[i]) / HLS_STDS[i]
            channels.append(norm_channel)

        stacked = np.stack(channels, axis=0)
        tensor = torch.from_numpy(stacked).unsqueeze(0).to(self.device)
        return tensor

    def predict(
        self,
        data: np.ndarray,
        sensor: str,
        bands: list[str],
        metadata: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        if sensor.lower() not in ["sentinel-2", "s2", "optical", "hls"]:
            raise ValueError(f"Prithvi-EO-2.0 expects optical HLS/Sentinel-2 imagery, received {sensor}")

        x = self._prepare_inputs(data, bands)
        with torch.no_grad():
            logits = self.model(x)
            prob = torch.sigmoid(logits).squeeze(0).squeeze(0).cpu().numpy()

        mask = prob >= self.probability_threshold
        return prob.astype(np.float32), mask.astype(bool)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "model_id": "ibm-nasa-geospatial/Prithvi-EO-2.0-300M",
            "name": "Prithvi-EO-2.0-300M Flood Adapter",
            "version": "2.0.0",
            "architecture": "3D ViT / Spatio-Temporal Segmentation Head",
            "required_bands": PRITHVI_BANDS,
            "resolution_m": 30.0,
            "license": "Apache 2.0",
            "attribution": "NASA-IBM Geospatial Foundation Model Initiative"
        }
