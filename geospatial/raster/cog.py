from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling


def write_cog(
    output_path: Path,
    data: np.ndarray,
    transform: rasterio.Affine,
    crs: str,
    nodata: float | None = None,
    dtype: str | None = None,
    compress: str = "deflate",
    overview_levels: list[int] | None = None
) -> Path:
    """
    Writes an array to a Cloud-Optimized GeoTIFF (COG) with tiled layout and overviews.
    Array shape can be (bands, height, width) or (height, width).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if data.ndim == 2:
        count = 1
        height, width = data.shape
        data_to_write = data[np.newaxis, :, :]
    elif data.ndim == 3:
        count, height, width = data.shape
        data_to_write = data
    else:
        raise ValueError(f"Expected 2D or 3D array, got shape {data.shape}")

    out_dtype = dtype or str(data.dtype)

    is_tiled = (width >= 256 and height >= 256)
    profile: dict[str, Any] = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": count,
        "dtype": out_dtype,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
        "compress": compress,
    }

    if is_tiled:
        profile["tiled"] = True
        profile["blockxsize"] = 256
        profile["blockysize"] = 256

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data_to_write.astype(out_dtype))

        # Build pyramid overviews if raster is sufficiently large
        if min(height, width) >= 256:
            levels = overview_levels or [2, 4, 8, 16]
            # filter levels that exceed raster size
            valid_levels = [lvl for lvl in levels if max(height, width) // lvl >= 64]
            if valid_levels:
                dst.build_overviews(valid_levels, Resampling.nearest)
                dst.update_tags(ns="rio_overview", resampling="nearest")

    return output_path
