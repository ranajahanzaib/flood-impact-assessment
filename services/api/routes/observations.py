import datetime
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from geospatial.ingestion.validator import validate_raster
from services.api.config import settings
from services.api.database import get_db
from services.api.models import FloodEvent, Observation
from services.api.schemas import ObservationResponse

router = APIRouter(prefix="", tags=["observations"])

@router.get("/events/{event_id}/observations", response_model=list[ObservationResponse])
def list_observations(event_id: str, db: Session = Depends(get_db)):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    obs_list = (
        db.query(Observation)
        .filter(Observation.event_id == event_id)
        .order_by(Observation.observation_time.asc())
        .all()
    )
    return obs_list

@router.post("/events/{event_id}/observations", response_model=ObservationResponse)
async def upload_observation(
    event_id: str,
    sensor: str = Form(..., description="sentinel-1, sentinel-2, dem"),
    observation_time: str = Form(...),
    event_phase: str = Form(..., description="before, during, after"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    obs_id = f"obs_{uuid.uuid4().hex[:8]}"
    upload_path = settings.UPLOADS_DIR / f"{obs_id}_{file.filename}"

    # Stream write upload
    with open(upload_path, "wb") as f:
        while chunk := await file.read(65536):
            f.write(chunk)

    try:
        # Validate georeferencing and CRS
        meta = validate_raster(upload_path, expected_sensor=sensor)
    except Exception as e:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=400, detail=f"Observation validation failed: {e!s}")

    obs_time = datetime.datetime.fromisoformat(observation_time.replace("Z", "+00:00"))

    observation = Observation(
        id=obs_id,
        event_id=event_id,
        sensor=sensor.lower(),
        observation_time=obs_time,
        event_phase=event_phase.lower(),
        file_path=str(upload_path),
        source="upload",
        bands=["VV", "VH"] if sensor == "sentinel-1" else ["B02", "B03", "B04", "B08"],
        crs=meta["crs"],
        resolution_m=meta["resolution_m"],
        nodata=meta["nodata"],
        checksum=meta["checksum"],
        metadata_json=meta
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation

@router.get("/observations/{observation_id}", response_model=ObservationResponse)
def get_observation(observation_id: str, db: Session = Depends(get_db)):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs

@router.delete("/observations/{observation_id}")
def delete_observation(observation_id: str, db: Session = Depends(get_db)):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")

    if Path(obs.file_path).exists():
        try:
            Path(obs.file_path).unlink()
        except Exception:
            pass

    db.delete(obs)
    db.commit()
    return {"message": "Observation deleted successfully"}
