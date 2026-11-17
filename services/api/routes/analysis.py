import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api.database import get_db
from services.api.models import AnalysisRun, FloodEvent, GeospatialOutput, ImpactMetrics
from services.api.schemas import (
    AnalysisRunCreate,
    AnalysisRunResponse,
    GeospatialOutputResponse,
    ImpactMetricsResponse,
)
from services.worker.pipelines.analysis_pipeline import run_flood_analysis_pipeline

router = APIRouter(prefix="", tags=["analysis"])

@router.post("/events/{event_id}/analysis", response_model=AnalysisRunResponse)
def trigger_analysis(
    event_id: str,
    payload: AnalysisRunCreate | None = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    ev = db.query(FloodEvent).filter(FloodEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")

    analysis_id = f"anl_{uuid.uuid4().hex[:8]}"
    config_dict = payload.config.dict() if payload and payload.config else {
        "method": "baseline",
        "output_crs": "EPSG:4326",
        "output_resolution_m": 10.0,
        "probability_threshold": 0.5
    }

    analysis = AnalysisRun(
        id=analysis_id,
        event_id=event_id,
        status="pending",
        config_json=config_dict,
        progress_pct=0,
        stage_message="Queued for execution"
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Launch pipeline in background task so HTTP request returns immediately
    if background_tasks:
        background_tasks.add_task(run_flood_analysis_pipeline, analysis_id)
    else:
        # Fallback synchronous execution if background tasks omitted
        run_flood_analysis_pipeline(analysis_id)
        db.refresh(analysis)

    return analysis

@router.get("/analysis/{analysis_id}", response_model=AnalysisRunResponse)
def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@router.post("/analysis/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status in ["completed", "failed"]:
        return {"message": f"Analysis already in terminal state: {analysis.status}"}

    analysis.status = "cancelled"
    analysis.stage_message = "Analysis cancelled by user"
    db.commit()
    return {"message": "Analysis cancelled successfully"}

@router.get("/analysis/{analysis_id}/outputs", response_model=list[GeospatialOutputResponse])
def get_analysis_outputs(analysis_id: str, db: Session = Depends(get_db)):
    outputs = db.query(GeospatialOutput).filter(GeospatialOutput.analysis_id == analysis_id).all()
    return outputs

@router.get("/analysis/{analysis_id}/metrics", response_model=ImpactMetricsResponse)
def get_analysis_metrics(analysis_id: str, db: Session = Depends(get_db)):
    metrics = db.query(ImpactMetrics).filter(ImpactMetrics.analysis_id == analysis_id).first()
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found for this analysis")
    return metrics
