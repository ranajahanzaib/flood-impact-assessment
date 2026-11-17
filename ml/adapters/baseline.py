from typing import Any

import numpy as np

from geospatial.water.dem import apply_topographic_constraint
from geospatial.water.optical import detect_water_s2
from geospatial.water.radar import detect_water_s1
from ml.models.base import ModelAdapter


class BaselineWaterAdapter(ModelAdapter):
    """
    Sensor-specific physical and index-based water & flood detection.
    Does not require downloading massive neural network weights.
    """

    def __init__(
        self,
        vv_threshold_db: float = -15.0,
        vh_threshold_db: float = -22.0,
        ndwi_threshold: float = 0.0,
        mndwi_threshold: float = 0.0,
        max_flood_slope_deg: float = 7.0,
        device=None
    ):
        super().__init__(device=device)
        self.vv_threshold_db = vv_threshold_db
        self.vh_threshold_db = vh_threshold_db
        self.ndwi_threshold = ndwi_threshold
        self.mndwi_threshold = mndwi_threshold
        self.max_flood_slope_deg = max_flood_slope_deg

    def predict(
        self,
        data: np.ndarray,
        sensor: str,
        bands: list[str],
        metadata: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Runs sensor-appropriate detection.
        """
        metadata = metadata or {}
        band_map = {b.upper(): i for i, b in enumerate(bands)}

        if sensor.lower() in ["sentinel-1", "s1", "sar"]:
            # Find VV and VH
            vv_idx = band_map.get("VV", 0)
            vv = data[vv_idx]
            vh = data[band_map["VH"]] if "VH" in band_map else None
            pre_vv = metadata.get("pre_vv")

            prob, mask = detect_water_s1(
                vv_band=vv,
                vh_band=vh,
                vv_threshold_db=self.vv_threshold_db,
                vh_threshold_db=self.vh_threshold_db,
                pre_vv_band=pre_vv
            )
        elif sensor.lower() in ["sentinel-2", "s2", "optical"]:
            # B03=Green, B04=Red, B02=Blue, B08=NIR, B11=SWIR
            green_idx = band_map.get("B03", band_map.get("GREEN", 1 if len(bands) > 1 else 0))
            nir_idx = band_map.get("B08", band_map.get("B8A", band_map.get("NIR", 3 if len(bands) > 3 else 0)))
            green = data[green_idx]
            nir = data[nir_idx]

            swir = data[band_map.get("B11", band_map.get("SWIR", 4))] if ("B11" in band_map or "SWIR" in band_map) and len(bands) > 4 else None
            blue = data[band_map.get("B02", band_map.get("BLUE", 0))] if ("B02" in band_map or "BLUE" in band_map) else None
            red = data[band_map.get("B04", band_map.get("RED", 2))] if ("B04" in band_map or "RED" in band_map) and len(bands) > 2 else None

            prob, mask, _ = detect_water_s2(
                green=green,
                nir=nir,
                swir=swir,
                blue=blue,
                red=red,
                ndwi_threshold=self.ndwi_threshold,
                mndwi_threshold=self.mndwi_threshold
            )
        else:
            raise ValueError(f"Unsupported sensor for baseline detection: {sensor}")

        # Apply topographic DEM constraint if available in metadata
        if "dem" in metadata:
            dem = metadata["dem"]
            prob, _ = apply_topographic_constraint(
                prob, dem, max_flood_slope_deg=self.max_flood_slope_deg
            )
            mask = prob >= 0.5

        return prob.astype(np.float32), mask.astype(bool)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "model_id": "baseline-radar-optical-v1",
            "name": "Multi-Sensor Physical Baseline",
            "version": "1.0.0",
            "type": "heuristic_physical",
            "supported_sensors": ["sentinel-1", "sentinel-2"],
            "parameters": {
                "vv_threshold_db": self.vv_threshold_db,
                "vh_threshold_db": self.vh_threshold_db,
                "ndwi_threshold": self.ndwi_threshold,
                "mndwi_threshold": self.mndwi_threshold,
                "max_flood_slope_deg": self.max_flood_slope_deg
            },
            "license": "MIT",
            "attribution": "ESA Sentinel-1 SAR Backscatter & Sentinel-2 NDWI/MNDWI Standards"
        }
