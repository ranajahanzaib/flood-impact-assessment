import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.api.config import settings


def generate_pdf_report(
    analysis_id: str,
    event_data: dict[str, Any],
    metrics_data: dict[str, Any],
    observations: list[dict[str, Any]],
    analysis_config: dict[str, Any],
    output_path: Path | None = None
) -> Path:
    """
    Generates a professional, multi-page flood evidence PDF report using ReportLab.
    """
    out_path = Path(output_path or settings.EXPORTS_DIR / f"flood_report_{analysis_id}.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    c_primary = colors.HexColor("#0f172a")  # Slate 900
    c_accent = colors.HexColor("#0284c7")   # Sky 600
    c_danger = colors.HexColor("#dc2626")   # Red 600
    c_muted = colors.HexColor("#64748b")    # Slate 500

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_muted,
        spaceAfter=14
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_primary,
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # 1. Header & Title
    story.append(Paragraph("FLOOD IMPACT ASSESSMENT", ParagraphStyle(
        "Pill", fontName="Helvetica-Bold", fontSize=9, textColor=c_accent, spaceAfter=4
    )))
    story.append(Paragraph(f"Impact Evidence Dossier: {event_data.get('name', 'Flood Event')}", title_style))
    story.append(Paragraph(
        f"Event ID: <b>{event_data.get('id')}</b> | Analysis ID: <b>{analysis_id}</b> | "
        f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    # 2. Executive Impact Summary Cards Table
    story.append(Paragraph("1. EXECUTIVE IMPACT SUMMARY", section_heading))

    newly_flooded_km2 = metrics_data.get("newly_flooded_km2", 0.0)
    preexisting_water_km2 = metrics_data.get("preexisting_water_km2", 0.0)
    total_water_km2 = metrics_data.get("total_water_km2", 0.0)
    receded_km2 = metrics_data.get("receded_km2", 0.0)
    affected_buildings = metrics_data.get("affected_buildings", 0)
    total_buildings = metrics_data.get("total_buildings", 0)
    affected_road_km = metrics_data.get("affected_road_km", 0.0)
    total_road_km = metrics_data.get("total_road_km", 0.0)

    summary_table_data = [
        [
            Paragraph("<b>Newly Inundated Land</b>", body_style),
            Paragraph(f"<font color='{c_danger}'><b>{newly_flooded_km2:,.2f} km²</b></font>", body_style),
            Paragraph("<b>Potentially Affected Buildings</b>", body_style),
            Paragraph(f"<b>{affected_buildings:,}</b> of {total_buildings:,}", body_style),
        ],
        [
            Paragraph("<b>Pre-Existing Water</b>", body_style),
            Paragraph(f"<b>{preexisting_water_km2:,.2f} km²</b>", body_style),
            Paragraph("<b>Inundated Road Length</b>", body_style),
            Paragraph(f"<b>{affected_road_km:,.2f} km</b> of {total_road_km:,.2f} km", body_style),
        ],
        [
            Paragraph("<b>Total Observed Water</b>", body_style),
            Paragraph(f"<b>{total_water_km2:,.2f} km²</b>", body_style),
            Paragraph("<b>Observed Recession Area</b>", body_style),
            Paragraph(f"<b>{receded_km2:,.2f} km²</b>", body_style),
        ]
    ]

    t_summary = Table(summary_table_data, colWidths=[140, 120, 160, 110])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 12))

    # 3. Observation Timeline & Multi-Sensor Table
    story.append(Paragraph("2. MULTI-SENSOR OBSERVATION RECONSTRUCTION", section_heading))
    obs_table_data = [
        [
            Paragraph("<b>Sensor</b>", body_style),
            Paragraph("<b>Phase</b>", body_style),
            Paragraph("<b>Acquisition Date/Time</b>", body_style),
            Paragraph("<b>Resolution</b>", body_style),
            Paragraph("<b>Status</b>", body_style)
        ]
    ]
    for obs in observations:
        obs_table_data.append([
            Paragraph(obs.get("sensor", "Unknown").upper(), body_style),
            Paragraph(obs.get("event_phase", "during").capitalize(), body_style),
            Paragraph(str(obs.get("observation_time", "N/A"))[:19], body_style),
            Paragraph(f"{obs.get('resolution_m', 10.0)} m", body_style),
            Paragraph("<font color='#16a34a'>Processed</font>", body_style)
        ])

    if len(obs_table_data) == 1:
        obs_table_data.append([Paragraph("No observations registered", body_style)] * 5)

    t_obs = Table(obs_table_data, colWidths=[90, 80, 170, 90, 100])
    t_obs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_obs)
    story.append(Spacer(1, 12))

    # 4. Infrastructure & Exposure Analysis
    story.append(Paragraph("3. INFRASTRUCTURE EXPOSURE & IMPACT METRICS", section_heading))
    infra_text = (
        "Infrastructure intersection is derived from spatial overlays with georeferenced building footprints "
        "and road vector centerlines. Terminology adheres to strict standards: intersecting features are classified "
        "as <i>potentially affected</i> or <i>intersecting observed inundation</i>; geometric intersection alone "
        "does not establish structural destruction or economic loss."
    )
    story.append(Paragraph(infra_text, body_style))
    story.append(Spacer(1, 8))

    # 5. Uncertainty & Limitations
    story.append(Paragraph("4. CONFIDENCE, UNCERTAINTY & LIMITATIONS", section_heading))
    uncert_km2 = metrics_data.get("uncertain_water_km2", 0.0)
    uncert_text = (
        f"<b>Uncertainty Assessment:</b> Approximately {uncert_km2:.2f} km² of candidate inundation "
        "exhibits elevated uncertainty due to prediction entropy, optical cloud/shadow attenuation, or "
        "radar-optical sensor disagreement. Regions flagged for human review remain isolated and documented "
        "in the accompanying GeoPackage vector layers."
    )
    story.append(Paragraph(uncert_text, body_style))
    story.append(Spacer(1, 8))

    # 6. Scientific Methodology & Attribution
    story.append(Paragraph("5. METHODOLOGY & PROVENANCE", section_heading))
    method_data = [
        [Paragraph("<b>Detection Engine</b>", body_style), Paragraph(str(analysis_config.get("method", "baseline")), body_style)],
        [Paragraph("<b>CRS / Map Grid</b>", body_style), Paragraph(str(analysis_config.get("output_crs", "EPSG:4326")), body_style)],
        [Paragraph("<b>Area Projection Method</b>", body_style), Paragraph("World Cylindrical Equal Area (EPSG:6933) metric geodesic transform", body_style)],
        [Paragraph("<b>Datasets & Attribution</b>", body_style), Paragraph("IBM, DLR & ESA Φ-lab (ImpactMesh-Flood, CC BY 4.0) | Copernicus Sentinel-1/2 | OpenStreetMap", body_style)],
    ]
    t_method = Table(method_data, colWidths=[150, 380])
    t_method.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_method)

    doc.build(story)
    return out_path
