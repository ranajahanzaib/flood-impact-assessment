from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from geospatial.ingestion.validator import validate_raster


class RasterReader:
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.metadata = validate_raster(self.file_path)

    @property
    def crs(self):
        return self.metadata["crs"]

    @property
    def bounds(self):
        return self.metadata["bounds"]

    @property
    def shape(self) -> tuple[int, int]:
        return (self.metadata["height"], self.metadata["width"])

    def read_window(
        self,
        window: Window | None = None,
        bands: list[int] | None = None
    ) -> tuple[np.ndarray, rasterio.Affine]:
        """
        Reads a window from the raster without loading the entire scene into memory.
        Returns:
            (array of shape [bands, height, width], window_transform)
        """
        with rasterio.open(self.file_path) as src:
            indexes = bands if bands is not None else list(range(1, src.count + 1))
            data = src.read(indexes, window=window)
            transform = rasterio.windows.transform(window, src.transform) if window else src.transform
            return data, transform

    def read_full(self) -> tuple[np.ndarray, rasterio.Affine]:
        return self.read_window(window=None)
