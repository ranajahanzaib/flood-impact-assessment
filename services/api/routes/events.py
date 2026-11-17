import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api.database import get_db
from services.api.models import AnalysisRun, FloodEvent, Observation
from services.api.schemas import FloodEventCreate, FloodEventResponse, FloodEventUpdate

router = APIRouter(prefix="/events", tags=["events"])

@router.get("", response_model=list[FloodEventResponse])
def list_events(db: Session = Depends(get_db)):
    events = db.query(FloodEvent).order_by(FloodEvent.created_at.desc()).all()
    results = []
    for ev in events:
        obs_count = db.query(Observation).filter(Observation.event_id == ev.id).count()
        latest_analysis = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.event_id == ev.id)
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
        results.append(FloodEventResponse(
            id=ev.id,
            name=ev.name,
            description=ev.description,
            country=ev.country,
            start_date=ev.start_date,
            end_date=ev.end_date,
            bounds_geojson=ev.bounds_geojson,
            status=ev.status,
            created_at=ev.created_at,
            observation_count=obs_count,
            latest_analysis_id=latest_analysis.id if latest_analysis else None
        ))
    return results

@router.post("", response_model=FloodEventResponse)
def create_event(payload: FloodEventCreate, db: Session = Depends(get_db)):
    event_id = payload.id or f"event_{uuid.uuid4().hex[:8]}"
    existing = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Event ID already exists")

    event = FloodEvent(
        id=event_id,
        name=payload.name,
        description=payload.description,
        country=payload.country,
        start_date=payload.start_date,
        end_date=payload.end_date,
        bounds_geojson=payload.bounds_geojson,
        status="active"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return FloodEventResponse(
        id=event.id,
        name=event.name,
        description=event.description,
        country=event.country,
        start_date=event.start_date,
        end_date=event.end_date,
        bounds_geojson=event.bounds_geojson,
        status=event.status,
        created_at=event.created_at,
        observation_count=0,
        latest_analysis_id=None
    )

@router.get("/{event_id}", response_model=FloodEventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    obs_count = db.query(Observation).filter(Observation.event_id == ev.id).count()
    latest_analysis = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.event_id == ev.id)
        .order_by(AnalysisRun.created_at.desc())
        .first()
    )
    return FloodEventResponse(
        id=ev.id,
        name=ev.name,
        description=ev.description,
        country=ev.country,
        start_date=ev.start_date,
        end_date=ev.end_date,
        bounds_geojson=ev.bounds_geojson,
        status=ev.status,
        created_at=ev.created_at,
        observation_count=obs_count,
        latest_analysis_id=latest_analysis.id if latest_analysis else None
    )

@router.patch("/{event_id}", response_model=FloodEventResponse)
def update_event(event_id: str, payload: FloodEventUpdate, db: Session = Depends(get_db)):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    if payload.name is not None:
        ev.name = payload.name
    if payload.description is not None:
        ev.description = payload.description
    if payload.status is not None:
        ev.status = payload.status
    if payload.bounds_geojson is not None:
        ev.bounds_geojson = payload.bounds_geojson

    db.commit()
    db.refresh(ev)
    return get_event(event_id, db)

@router.delete("/{event_id}")
def delete_event(event_id: str, db: Session = Depends(get_db)):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(ev)
    db.commit()
    return {"message": "Event deleted successfully"}
