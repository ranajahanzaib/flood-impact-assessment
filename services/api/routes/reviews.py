import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api.database import get_db
from services.api.models import AnalysisRun, ReviewRegion
from services.api.schemas import ReviewDecisionRequest, ReviewRegionResponse

router = APIRouter(prefix="", tags=["reviews"])

@router.get("/analysis/{analysis_id}/review-regions", response_model=list[ReviewRegionResponse])
def list_review_regions(analysis_id: str, db: Session = Depends(get_db)):
    regions = db.query(ReviewRegion).filter(ReviewRegion.analysis_id == analysis_id).all()
    return regions

@router.post("/review-regions/{region_id}/decision", response_model=ReviewRegionResponse)
def submit_review_decision(region_id: str, payload: ReviewDecisionRequest, db: Session = Depends(get_db)):
    reg = db.query(ReviewRegion).filter(ReviewRegion.id == region_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Review region not found")

    valid_decisions = ["confirmed_flood", "confirmed_dry", "dismissed"]
    if payload.decision not in valid_decisions:
        raise HTTPException(status_code=400, detail=f"Invalid decision. Must be one of {valid_decisions}")

    reg.status = payload.decision
    reg.reviewer_notes = payload.notes
    reg.reviewed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(reg)
    return reg

@router.get("/events/{event_id}/review-history", response_model=list[ReviewRegionResponse])
def get_event_review_history(event_id: str, db: Session = Depends(get_db)):
    analyses = db.query(AnalysisRun).filter(AnalysisRun.event_id == event_id).all()
    analysis_ids = [a.id for a in analyses]
    regions = (
        db.query(ReviewRegion)
        .filter(ReviewRegion.analysis_id.in_(analysis_ids))
        .filter(ReviewRegion.status != "pending")
        .all()
    )
    return regions
