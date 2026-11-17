from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import Resampling, calculate_default_transform, reproject


@dataclass
class TargetGrid:
    crs: str
    transform: rasterio.Affine
    width: int
    height: int
    resolution_m: float
    bounds: tuple[float, float, float, float]  # left, bottom, right, top

def create_target_grid(
    bounds: tuple[float, float, float, float],
    source_crs: str,
    target_crs: str = "EPSG:3857",
    resolution_m: float = 10.0
) -> TargetGrid:
    """
    Creates a target grid specification from bounds.
    If target_crs is in degrees (like EPSG:4326), converts resolution_m to degrees approximately.
    """
    left, bottom, right, top = bounds
    t_crs = CRS.from_string(target_crs)
    s_crs = CRS.from_string(source_crs)

    # Calculate transformation
    transform, width, height = calculate_default_transform(
        s_crs, t_crs,
        width=int(abs(right - left) / resolution_m) or 256,
        height=int(abs(top - bottom) / resolution_m) or 256,
        left=left, bottom=bottom, right=right, top=top,
        resolution=(resolution_m, resolution_m) if t_crs.is_projected else None
    )

    return TargetGrid(
        crs=target_crs,
        transform=transform,
        width=width,
        height=height,
        resolution_m=resolution_m,
        bounds=bounds
    )

def align_raster_to_grid(
    src_data: np.ndarray,
    src_transform: rasterio.Affine,
    src_crs: str,
    target_grid: TargetGrid,
    src_nodata: float | None = None,
    target_nodata: float = -9999.0,
    is_categorical: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """
    Reprojects and aligns raster data to the TargetGrid.
    Returns:
        (aligned_data, valid_mask):
        aligned_data: shape (bands, height, width)
        valid_mask: boolean shape (height, width) where True means observation was valid & non-nodata
    """
    if src_data.ndim == 2:
        src_data = src_data[np.newaxis, :, :]

    count = src_data.shape[0]
    out_data = np.full((count, target_grid.height, target_grid.width), target_nodata, dtype=src_data.dtype)

    resample_alg = Resampling.nearest if is_categorical else Resampling.bilinear

    for b in range(count):
        reproject(
            source=src_data[b],
            destination=out_data[b],
            src_transform=src_transform,
            src_crs=CRS.from_string(src_crs),
            dst_transform=target_grid.transform,
            dst_crs=CRS.from_string(target_grid.crs),
            src_nodata=src_nodata,
            dst_nodata=target_nodata,
            resampling=resample_alg
        )

    # Compute valid mask: valid where all bands are != target_nodata and not NaN
    if np.issubdtype(out_data.dtype, np.floating):
        valid_mask = ~np.isnan(out_data[0]) & (out_data[0] != target_nodata)
    else:
        valid_mask = (out_data[0] != target_nodata)

    return out_data, valid_mask
