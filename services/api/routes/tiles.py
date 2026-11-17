import io
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from PIL import Image
from sqlalchemy.orm import Session

from services.api.database import get_db
from services.api.models import GeospatialOutput

router = APIRouter(prefix="", tags=["tiles"])

@router.get("/tiles/raster/{output_id}/preview.png")
def get_raster_preview(output_id: str, db: Session = Depends(get_db)):
    output = db.query(GeospatialOutput).filter(GeospatialOutput.id == output_id).first()
    if not output or not Path(output.file_path).exists():
        raise HTTPException(status_code=404, detail="Raster output not found")

    try:
        with rasterio.open(output.file_path) as src:
            data = src.read(1)
            # Resize thumbnail if huge
            h, w = data.shape
            scale = max(1, max(h, w) // 1024)
            if scale > 1:
                data = data[::scale, ::scale]

        # Apply appropriate color map
        rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)

        if output.product_type in ["new_inundation", "flooded_polygons"]:
            # Red/Orange for new inundation
            flood_mask = data > 0
            rgba[flood_mask] = [239, 68, 68, 200]  # #ef4444
        elif output.product_type == "flood_classification":
            # 1 = permanent (deep sky blue), 2 = new inundation (red), 3 = receded (green)
            rgba[data == 1] = [2, 132, 199, 180]   # Sky blue
            rgba[data == 2] = [239, 68, 68, 220]   # Red
            rgba[data == 3] = [16, 185, 129, 180]  # Green
        elif output.product_type == "temporal_persistence":
            # Colormap from cyan to deep indigo
            ratio = np.clip(data, 0.0, 1.0)
            valid = ratio > 0
            rgba[valid, 0] = (255 * (1.0 - ratio[valid])).astype(np.uint8)
            rgba[valid, 1] = (180 * ratio[valid]).astype(np.uint8)
            rgba[valid, 2] = 235
            rgba[valid, 3] = (ratio[valid] * 200 + 40).astype(np.uint8)
        elif output.product_type == "uncertainty":
            # Amber to Red
            u = np.clip(data, 0.0, 1.0)
            high_u = u > 0.3
            rgba[high_u, 0] = 245
            rgba[high_u, 1] = (158 * (1.0 - u[high_u])).astype(np.uint8)
            rgba[high_u, 2] = 11
            rgba[high_u, 3] = (u[high_u] * 200).astype(np.uint8)
        else:
            # Grayscale / probability
            norm = np.clip(data * 255.0, 0, 255).astype(np.uint8)
            rgba[:, :, 0] = norm
            rgba[:, :, 1] = norm
            rgba[:, :, 2] = norm
            rgba[:, :, 3] = np.where(norm > 20, 180, 0)

        img = Image.fromarray(rgba, "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate raster preview: {e!s}")

@router.get("/vector/{output_id}/geojson")
def get_vector_geojson(output_id: str, db: Session = Depends(get_db)):
    output = db.query(GeospatialOutput).filter(GeospatialOutput.id == output_id).first()
    if not output or not Path(output.file_path).exists():
        raise HTTPException(status_code=404, detail="Vector output not found")

    try:
        gdf = gpd.read_file(output.file_path)
        # Ensure EPSG:4326 for GeoJSON output
        if gdf.crs and not gdf.crs.equals("EPSG:4326"):
            gdf = gdf.to_crs(epsg=4326)

        # Limit feature count or simplify slightly if huge
        if len(gdf) > 5000:
            gdf = gdf.head(5000)

        return JSONResponse(content=gdf.__geo_interface__)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load vector GeoJSON: {e!s}")
