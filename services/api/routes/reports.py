from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from services.api.database import get_db
from services.api.models import GeospatialOutput

router = APIRouter(prefix="", tags=["reports"])

@router.get("/reports/{analysis_id}/download")
def download_evidence_package(analysis_id: str, db: Session = Depends(get_db)):
    output = (
        db.query(GeospatialOutput)
        .filter(GeospatialOutput.analysis_id == analysis_id, GeospatialOutput.product_type == "evidence_package")
        .first()
    )
    if not output or not Path(output.file_path).exists():
        raise HTTPException(status_code=404, detail="Evidence package ZIP not found")

    return FileResponse(
        path=output.file_path,
        filename=f"flood_evidence_{analysis_id}.zip",
        media_type="application/zip"
    )

@router.get("/reports/{analysis_id}/pdf")
def download_pdf_report(analysis_id: str, db: Session = Depends(get_db)):
    output = (
        db.query(GeospatialOutput)
        .filter(GeospatialOutput.analysis_id == analysis_id, GeospatialOutput.product_type == "pdf_report")
        .first()
    )
    if not output or not Path(output.file_path).exists():
        raise HTTPException(status_code=404, detail="PDF report not found")

    return FileResponse(
        path=output.file_path,
        filename=f"flood_report_{analysis_id}.pdf",
        media_type="application/pdf"
    )
