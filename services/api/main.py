from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from services.api.config import settings
from services.api.database import init_db
from services.api.models import AnalysisRun, FloodEvent, ImpactMetrics, ReviewRegion
from services.api.routes import (
    analysis,
    events,
    infrastructure,
    observations,
    reports,
    reviews,
    tiles,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-Sensor Flood Impact Evidence Platform API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(events.router, prefix=settings.API_PREFIX)
app.include_router(observations.router, prefix=settings.API_PREFIX)
app.include_router(analysis.router, prefix=settings.API_PREFIX)
app.include_router(infrastructure.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(reviews.router, prefix=settings.API_PREFIX)
app.include_router(tiles.router, prefix=settings.API_PREFIX)


@app.get(f"{settings.API_PREFIX}/health")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get(f"{settings.API_PREFIX}/overview")
def get_overview_statistics():
    from services.api.database import SessionLocal

    db: Session = SessionLocal()
    try:
        total_events = db.query(FloodEvent).count()
        total_analyses = db.query(AnalysisRun).count()

        all_metrics = db.query(ImpactMetrics).all()
        total_newly_flooded_km2 = sum(m.newly_flooded_m2 for m in all_metrics) / 1e6
        total_affected_buildings = sum(m.affected_buildings for m in all_metrics)
        total_affected_road_km = sum(m.affected_road_meters for m in all_metrics) / 1000.0

        pending_reviews = db.query(ReviewRegion).filter(ReviewRegion.status == "pending").count()

        recent_events = db.query(FloodEvent).order_by(FloodEvent.created_at.desc()).limit(5).all()

        return {
            "total_events": total_events,
            "total_analyses": total_analyses,
            "total_newly_flooded_km2": round(total_newly_flooded_km2, 2),
            "total_affected_buildings": total_affected_buildings,
            "total_affected_road_km": round(total_affected_road_km, 2),
            "pending_manual_reviews": pending_reviews,
            "recent_events": [
                {"id": ev.id, "name": ev.name, "country": ev.country, "created_at": ev.created_at}
                for ev in recent_events
            ],
        }
    finally:
        db.close()
