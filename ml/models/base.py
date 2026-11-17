from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import torch


def get_compute_device() -> torch.device:
    """
    Selects the best available hardware accelerator:
    CUDA -> Apple Silicon MPS -> CPU
    """
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

class ModelAdapter(ABC):
    """
    Common abstraction for Earth-Observation water & flood detection models.
    Decouples geospatial pipeline from specific ML model backbones.
    """

    def __init__(self, device: torch.device | None = None):
        self.device = device or get_compute_device()

    @abstractmethod
    def predict(
        self,
        data: np.ndarray,
        sensor: str,
        bands: list[str],
        metadata: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Runs inference on prepared observation data.
        
        Args:
            data: shape (bands, height, width)
            sensor: 'sentinel-1' or 'sentinel-2'
            bands: list of band names
            metadata: acquisition timestamps, DEM, etc.
            
        Returns:
            (probability_raster, binary_water_mask):
            probability_raster: float32 in [0, 1] of shape (height, width)
            binary_water_mask: bool of shape (height, width)
        """

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """
        Returns model specifications, version, input channels, license, and provenance.
        """
