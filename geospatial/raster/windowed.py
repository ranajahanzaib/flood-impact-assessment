from collections.abc import Iterator

from rasterio.windows import Window


def generate_windows(
    width: int,
    height: int,
    tile_size: int = 512,
    overlap: int = 0
) -> Iterator[tuple[Window, Window]]:
    """
    Yields (read_window, write_window) across the raster dimensions.
    Allows overlapping reads with non-overlapping writes to avoid edge artifacts.
    """
    step = tile_size - (2 * overlap)
    if step <= 0:
        step = tile_size

    for row_start in range(0, height, step):
        row_end = min(row_start + step, height)
        # Read window with padding
        r_row_start = max(0, row_start - overlap)
        r_row_end = min(height, row_end + overlap)

        for col_start in range(0, width, step):
            col_end = min(col_start + step, width)
            c_col_start = max(0, col_start - overlap)
            c_col_end = min(width, col_end + overlap)

            read_window = Window.from_slices(
                slice(r_row_start, r_row_end),
                slice(c_col_start, c_col_end)
            )
            write_window = Window.from_slices(
                slice(row_start, row_end),
                slice(col_start, col_end)
            )
            yield read_window, write_window
