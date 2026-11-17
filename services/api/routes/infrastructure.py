import uuid

import geopandas as gpd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from geospatial.infrastructure.osm import query_osm_infrastructure
from services.api.config import settings
from services.api.database import get_db
from services.api.models import FloodEvent, InfrastructureDataset
from services.api.schemas import InfrastructureImportRequest, InfrastructureResponse

router = APIRouter(prefix="", tags=["infrastructure"])

@router.get("/events/{event_id}/infrastructure", response_model=list[InfrastructureResponse])
def list_infrastructure(event_id: str, db: Session = Depends(get_db)):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    return db.query(InfrastructureDataset).filter(InfrastructureDataset.event_id == event_id).all()

@router.post("/events/{event_id}/infrastructure/import", response_model=list[InfrastructureResponse])
def import_infrastructure_osm(
    event_id: str,
    payload: InfrastructureImportRequest,
    db: Session = Depends(get_db)
):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    bbox = payload.osm_query_bbox or ev.bounds_geojson
    if not bbox or len(bbox) < 4:
        raise HTTPException(status_code=400, detail="Bounding box [min_lon, min_lat, max_lon, max_lat] is required")

    results = []
    for layer in payload.layer_types:
        gdf = query_osm_infrastructure(bbox, layer_type=layer)
        layer_id = f"infra_{uuid.uuid4().hex[:8]}"
        dest_file = settings.PROCESSED_DIR / f"{layer}_{event_id}.gpkg"

        feature_count = len(gdf)
        if not gdf.empty:
            gdf.to_file(dest_file, driver="GPKG", layer=layer)
        else:
            # write empty dummy GeoPackage
            gdf.to_file(dest_file, driver="GPKG", layer=layer)

        infra_record = InfrastructureDataset(
            id=layer_id,
            event_id=event_id,
            layer_type=layer,
            source="osm",
            file_path=str(dest_file),
            feature_count=feature_count
        )
        db.add(infra_record)
        db.commit()
        db.refresh(infra_record)
        results.append(infra_record)

    return results

@router.post("/events/{event_id}/infrastructure/upload", response_model=InfrastructureResponse)
async def upload_infrastructure(
    event_id: str,
    layer_type: str = Form(..., description="buildings or roads"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    layer_id = f"infra_{uuid.uuid4().hex[:8]}"
    upload_path = settings.UPLOADS_DIR / f"{layer_id}_{file.filename}"

    with open(upload_path, "wb") as f:
        while chunk := await file.read(65536):
            f.write(chunk)

    try:
        gdf = gpd.read_file(upload_path)
        feature_count = len(gdf)
    except Exception as e:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to parse vector layer: {e!s}")

    infra_record = InfrastructureDataset(
        id=layer_id,
        event_id=event_id,
        layer_type=layer_type,
        source="upload",
        file_path=str(upload_path),
        feature_count=feature_count
    )
    db.add(infra_record)
    db.commit()
    db.refresh(infra_record)
    return infra_record
