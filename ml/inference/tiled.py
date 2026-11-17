
import numpy as np

from geospatial.raster.windowed import generate_windows
from ml.models.base import ModelAdapter


def run_tiled_inference(
    adapter: ModelAdapter,
    raster_data: np.ndarray,
    sensor: str,
    bands: list[str],
    tile_size: int = 512,
    overlap: int = 32,
    batch_size: int = 4,
    metadata: dict | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Executes windowed / tiled model inference to keep peak RAM usage low
    and prevent GPU/CPU Out-Of-Memory errors on massive satellite scenes.
    """
    if raster_data.ndim == 2:
        raster_data = raster_data[np.newaxis, :, :]

    count, height, width = raster_data.shape

    # If small enough, run directly without tiling overhead
    if height <= tile_size and width <= tile_size:
        return adapter.predict(raster_data, sensor, bands, metadata)

    prob_accum = np.zeros((height, width), dtype=np.float32)
    weight_accum = np.zeros((height, width), dtype=np.float32)

    for read_win, write_win in generate_windows(width, height, tile_size=tile_size, overlap=overlap):
        # Slice input tile
        tile_data = raster_data[:, read_win.row_off : read_win.row_off + read_win.height,
                                read_win.col_off : read_win.col_off + read_win.width]

        tile_prob, _ = adapter.predict(tile_data, sensor, bands, metadata)

        # Generate 2D blend weights (linear ramp at boundaries)
        h, w = tile_prob.shape
        weight_y = np.minimum(np.arange(h) + 1, h - np.arange(h))
        weight_x = np.minimum(np.arange(w) + 1, w - np.arange(w))
        weight_2d = np.minimum.outer(weight_y, weight_x).astype(np.float32)
        weight_2d /= np.max(weight_2d)

        # Accumulate
        r_slice = slice(read_win.row_off, read_win.row_off + read_win.height)
        c_slice = slice(read_win.col_off, read_win.col_off + read_win.width)

        prob_accum[r_slice, c_slice] += tile_prob * weight_2d
        weight_accum[r_slice, c_slice] += weight_2d

    # Normalize by accumulated weights
    valid_weights = weight_accum > 0
    prob_accum[valid_weights] /= weight_accum[valid_weights]
    prob_accum = np.clip(prob_accum, 0.0, 1.0)

    mask = prob_accum >= 0.5
    return prob_accum, mask
