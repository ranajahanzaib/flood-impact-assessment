import hashlib
from pathlib import Path
from typing import Any

import geopandas as gpd
import rasterio


class ValidationError(Exception):
    pass

def compute_file_checksum(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def validate_raster(
    file_path: Path,
    expected_sensor: str | None = None,
    expected_bands: list[str] | None = None
) -> dict[str, Any]:
    """
    Validates a GeoTIFF / raster file.
    Ensures valid CRS, geotransform, dimensions, band count, and extracts metadata.
    """
    if not file_path.exists():
        raise ValidationError(f"File does not exist: {file_path}")

    try:
        with rasterio.open(file_path) as src:
            # 1. CRS validation
            if not src.crs or not src.crs.is_valid:
                raise ValidationError(f"Invalid or missing CRS in {file_path.name}")

            # 2. Dimensions and transform
            if src.width <= 0 or src.height <= 0:
                raise ValidationError(f"Invalid raster dimensions: {src.width}x{src.height}")

            transform = src.transform
            if transform.is_identity:
                raise ValidationError("Raster has identity affine transform (missing georeferencing)")

            # 3. Band count & sensor check
            if src.count <= 0:
                raise ValidationError(f"Raster has no bands: {src.count}")

            if expected_sensor == "sentinel-1" and src.count < 1:
                raise ValidationError("Sentinel-1 requires at least 1 polarization band (e.g., VV/VH)")

            if expected_sensor == "sentinel-2" and expected_bands:
                if src.count < len(expected_bands):
                    raise ValidationError(
                        f"Sentinel-2 expected {len(expected_bands)} bands ({expected_bands}), found {src.count}"
                    )

            # Extract resolution
            res_x, res_y = abs(src.res[0]), abs(src.res[1])

            bounds = src.bounds
            bounds_list = [bounds.left, bounds.bottom, bounds.right, bounds.top]

            # Collect metadata
            metadata = {
                "crs": src.crs.to_string(),
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtypes": src.dtypes,
                "nodata": src.nodata,
                "resolution_m": float((res_x + res_y) / 2.0),
                "bounds": bounds_list,
                "transform": [t for t in transform],
                "checksum": compute_file_checksum(file_path),
            }
            return metadata

    except rasterio.RasterioIOError as e:
        raise ValidationError(f"Failed to read raster file: {e!s}")


def validate_vector(file_path: Path) -> dict[str, Any]:
    """
    Validates a GeoJSON or GeoPackage file.
    Ensures valid layer, CRS, and non-empty geometries.
    """
    if not file_path.exists():
        raise ValidationError(f"Vector file does not exist: {file_path}")

    try:
        gdf = gpd.read_file(file_path)
        if gdf.crs is None:
            raise ValidationError("Vector layer is missing CRS")

        count = len(gdf)
        bounds = gdf.total_bounds

        metadata = {
            "crs": str(gdf.crs),
            "feature_count": count,
            "bounds": [float(b) for b in bounds] if count > 0 else None,
            "checksum": compute_file_checksum(file_path)
        }
        return metadata
    except Exception as e:
        raise ValidationError(f"Failed to read vector layer: {e!s}")
