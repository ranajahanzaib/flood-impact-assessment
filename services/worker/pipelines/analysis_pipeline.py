import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np

from geospatial.export.package import create_evidence_package
from geospatial.flood.extent import polygonize_flood_mask
from geospatial.flood.permanent import separate_permanent_and_flood_water
from geospatial.flood.persistence import calculate_temporal_persistence
from geospatial.infrastructure.intersection import analyze_building_impact, analyze_road_impact
from geospatial.infrastructure.osm import query_osm_infrastructure
from geospatial.ingestion.reader import RasterReader
from geospatial.metrics.area import calculate_impact_areas
from geospatial.raster.cog import write_cog
from geospatial.reprojection.grid import align_raster_to_grid, create_target_grid
from geospatial.uncertainty.signals import (
    build_composite_uncertainty,
    detect_sensor_disagreement,
    extract_manual_review_regions,
)
from ml.adapters.baseline import BaselineWaterAdapter
from ml.adapters.clay import ClayAdapter
from ml.adapters.prithvi import PrithviAdapter
from reports.pdf_generator import generate_pdf_report
from services.api.config import settings
from services.api.database import SessionLocal
from services.api.models import (
    AnalysisRun,
    FloodEvent,
    GeospatialOutput,
    ImpactMetrics,
    InfrastructureDataset,
    Observation,
    ReviewRegion,
)


def run_flood_analysis_pipeline(analysis_id: str):
    """
    Complete end-to-end multi-sensor flood impact evidence reconstruction pipeline.
    """
    db = SessionLocal()
    try:
        analysis: AnalysisRun = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        if not analysis:
            return

        analysis.status = "running"
        analysis.started_at = datetime.datetime.utcnow()
        analysis.progress_pct = 5
        analysis.stage_message = "Validating event observations"
        db.commit()

        event: FloodEvent = db.query(FloodEvent).filter(FloodEvent.id == analysis.event_id).first()
        config: dict[str, Any] = analysis.config_json or {}
        observations: list[Observation] = (
            db.query(Observation)
            .filter(Observation.event_id == event.id)
            .order_by(Observation.observation_time.asc())
            .all()
        )

        if not observations:
            analysis.status = "failed"
            analysis.error_message = "No observations found for event"
            db.commit()
            return

        # 1. Determine analysis bounds and create TargetGrid
        readers = [RasterReader(Path(obs.file_path)) for obs in observations]
        min_lon = min(r.bounds[0] for r in readers)
        min_lat = min(r.bounds[1] for r in readers)
        max_lon = max(r.bounds[2] for r in readers)
        max_lat = max(r.bounds[3] for r in readers)
        bounds = (min_lon, min_lat, max_lon, max_lat)

        target_grid = create_target_grid(
            bounds=bounds,
            source_crs=readers[0].crs,
            target_crs=config.get("output_crs", "EPSG:4326"),
            resolution_m=config.get("output_resolution_m", 10.0)
        )

        analysis.progress_pct = 20
        analysis.stage_message = "Harmonizing observations onto common spatial grid"
        db.commit()

        # 2. Select Model Adapter
        method = config.get("method", "baseline")
        if method == "prithvi":
            adapter = PrithviAdapter()
        elif method == "clay":
            adapter = ClayAdapter()
        else:
            adapter = BaselineWaterAdapter()

        # 3. Process Observations & Group by Phase
        pre_water_masks = []
        pre_valid_masks = []
        during_water_masks = []
        during_valid_masks = []
        during_probs = []
        post_water_masks = []
        post_valid_masks = []
        obs_timestamps = []

        processed_dir = settings.PROCESSED_DIR / analysis.id
        processed_dir.mkdir(parents=True, exist_ok=True)
        raster_paths = {}

        # S1 vs S2 probability rasters for disagreement detection
        last_s1_prob = None
        last_s2_prob = None
        last_s2_valid = None

        for obs, reader in zip(observations, readers):
            raw_data, transform = reader.read_full()
            aligned_data, valid_mask = align_raster_to_grid(
                src_data=raw_data,
                src_transform=transform,
                src_crs=reader.crs,
                target_grid=target_grid,
                src_nodata=obs.nodata
            )

            # Predict water probability
            prob, mask = adapter.predict(
                aligned_data,
                sensor=obs.sensor,
                bands=obs.bands or ["VV", "VH"] if obs.sensor == "sentinel-1" else ["B02", "B03", "B04", "B08"]
            )
            prob[~valid_mask] = 0.0
            mask[~valid_mask] = False

            if obs.sensor == "sentinel-1":
                last_s1_prob = prob
            elif obs.sensor == "sentinel-2":
                last_s2_prob = prob
                last_s2_valid = valid_mask

            if obs.event_phase == "before":
                pre_water_masks.append(mask)
                pre_valid_masks.append(valid_mask)
            elif obs.event_phase == "during":
                during_water_masks.append(mask)
                during_valid_masks.append(valid_mask)
                during_probs.append(prob)
                obs_timestamps.append(obs.observation_time.isoformat())
            elif obs.event_phase == "after":
                post_water_masks.append(mask)
                post_valid_masks.append(valid_mask)

        # Baseline Pre-existing water mask
        if pre_water_masks:
            pre_water_combined = np.logical_or.reduce(pre_water_masks)
            pre_valid_combined = np.logical_or.reduce(pre_valid_masks)
        else:
            pre_water_combined = np.zeros((target_grid.height, target_grid.width), dtype=bool)
            pre_valid_combined = np.ones((target_grid.height, target_grid.width), dtype=bool)

        # During-event combined water
        if during_water_masks:
            during_water_combined = np.logical_or.reduce(during_water_masks)
            during_valid_combined = np.logical_or.reduce(during_valid_masks)
            during_prob_combined = np.maximum.reduce(during_probs)
        else:
            during_water_combined = np.zeros((target_grid.height, target_grid.width), dtype=bool)
            during_valid_combined = np.ones((target_grid.height, target_grid.width), dtype=bool)
            during_prob_combined = np.zeros((target_grid.height, target_grid.width), dtype=np.float32)

        # Post-event recession
        post_water_combined = np.logical_or.reduce(post_water_masks) if post_water_masks else None
        post_valid_combined = np.logical_or.reduce(post_valid_masks) if post_valid_masks else None

        analysis.progress_pct = 45
        analysis.stage_message = "Separating pre-existing water and measuring flood extent"
        db.commit()

        # 4. Permanent vs Newly Inundated Separation
        class_raster, new_inundation_mask = separate_permanent_and_flood_water(
            pre_water_mask=pre_water_combined,
            pre_valid_mask=pre_valid_combined,
            during_water_mask=during_water_combined,
            during_valid_mask=during_valid_combined,
            post_water_mask=post_water_combined,
            post_valid_mask=post_valid_combined
        )

        # Save classification COG
        class_cog_path = processed_dir / "classification_raster.tif"
        write_cog(class_cog_path, class_raster, target_grid.transform, target_grid.crs, nodata=255, dtype="uint8")
        raster_paths["classification"] = class_cog_path
        db.add(GeospatialOutput(
            id=f"out_class_{analysis.id}",
            analysis_id=analysis.id,
            product_type="flood_classification",
            file_path=str(class_cog_path),
            format="cog"
        ))

        # Save new inundation COG
        new_inundation_cog = processed_dir / "new_inundation.tif"
        write_cog(new_inundation_cog, new_inundation_mask.astype(np.uint8), target_grid.transform, target_grid.crs, dtype="uint8")
        raster_paths["maximum_observed_inundation"] = new_inundation_cog
        db.add(GeospatialOutput(
            id=f"out_new_inundation_{analysis.id}",
            analysis_id=analysis.id,
            product_type="new_inundation",
            file_path=str(new_inundation_cog),
            format="cog"
        ))

        # 5. Temporal Persistence
        persistence_data = calculate_temporal_persistence(
            observation_masks=during_water_masks if during_water_masks else [during_water_combined],
            observation_valid_masks=during_valid_masks if during_valid_masks else [during_valid_combined],
            observation_timestamps=obs_timestamps if obs_timestamps else ["default"]
        )
        persist_cog = processed_dir / "temporal_persistence.tif"
        write_cog(persist_cog, persistence_data["persistence_ratio"], target_grid.transform, target_grid.crs, dtype="float32")
        raster_paths["temporal_persistence"] = persist_cog
        db.add(GeospatialOutput(
            id=f"out_persist_{analysis.id}",
            analysis_id=analysis.id,
            product_type="persistence",
            file_path=str(persist_cog),
            format="cog"
        ))

        # 6. Uncertainty Assessment & Sensor Disagreement
        sensor_disagree_mask = None
        if last_s1_prob is not None and last_s2_prob is not None and last_s2_valid is not None:
            _, sensor_disagree_mask = detect_sensor_disagreement(last_s1_prob, last_s2_prob, last_s2_valid)

        uncertainty_raster, high_uncert_mask = build_composite_uncertainty(
            water_prob=during_prob_combined,
            valid_mask=during_valid_combined,
            sensor_disagreement=sensor_disagree_mask.astype(float) if sensor_disagree_mask is not None else None,
            observation_gap_mask=persistence_data["observation_gap_flag"]
        )
        uncert_cog = processed_dir / "uncertainty.tif"
        write_cog(uncert_cog, uncertainty_raster, target_grid.transform, target_grid.crs, dtype="float32")
        raster_paths["uncertainty"] = uncert_cog
        db.add(GeospatialOutput(
            id=f"out_uncert_{analysis.id}",
            analysis_id=analysis.id,
            product_type="uncertainty",
            file_path=str(uncert_cog),
            format="cog"
        ))

        # Extract manual review regions
        review_regions = extract_manual_review_regions(
            uncertainty_raster, target_grid.transform, target_grid.crs, sensor_disagreement_mask=sensor_disagree_mask
        )
        for i, reg in enumerate(review_regions):
            db.add(ReviewRegion(
                id=f"rev_{analysis.id}_{i}",
                analysis_id=analysis.id,
                geometry_json=reg["geometry"],
                flag_type=reg["flag_type"],
                reason=reg["reason"]
            ))

        analysis.progress_pct = 65
        analysis.stage_message = "Polygonizing flood masks & intersecting infrastructure"
        db.commit()

        # 7. Polygonize Flood Extent into Vector GeoPackage
        vector_paths = {}
        flood_gdf = polygonize_flood_mask(class_raster, target_grid.transform, target_grid.crs)
        flood_gpkg_path = processed_dir / "inundated_regions.gpkg"
        if not flood_gdf.empty:
            flood_gdf.to_file(flood_gpkg_path, driver="GPKG", layer="inundated_regions")
            vector_paths["inundated_regions"] = flood_gpkg_path
            db.add(GeospatialOutput(
                id=f"out_vec_flood_{analysis.id}",
                analysis_id=analysis.id,
                product_type="flooded_polygons",
                file_path=str(flood_gpkg_path),
                format="gpkg"
            ))

        # 8. Infrastructure Impact Analysis
        # Check if infrastructure layers already imported or query OSM
        buildings_ds = db.query(InfrastructureDataset).filter(
            InfrastructureDataset.event_id == event.id,
            InfrastructureDataset.layer_type == "buildings"
        ).first()

        roads_ds = db.query(InfrastructureDataset).filter(
            InfrastructureDataset.event_id == event.id,
            InfrastructureDataset.layer_type == "roads"
        ).first()

        if buildings_ds and Path(buildings_ds.file_path).exists():
            buildings_gdf = gpd.read_file(buildings_ds.file_path)
        else:
            buildings_gdf = query_osm_infrastructure(list(bounds), layer_type="buildings")

        if roads_ds and Path(roads_ds.file_path).exists():
            roads_gdf = gpd.read_file(roads_ds.file_path)
        else:
            roads_gdf = query_osm_infrastructure(list(bounds), layer_type="roads")

        # Candidate newly inundated polygons for intersection
        candidate_flood_gdf = flood_gdf[flood_gdf["class_name"] == "new_inundation"] if not flood_gdf.empty else flood_gdf

        affected_buildings_gdf, building_stats = analyze_building_impact(buildings_gdf, candidate_flood_gdf)
        affected_roads_gdf, road_stats = analyze_road_impact(roads_gdf, candidate_flood_gdf)

        # Save affected infrastructure layers
        if not affected_buildings_gdf.empty:
            bldg_path = processed_dir / "affected_buildings.gpkg"
            affected_buildings_gdf.to_file(bldg_path, driver="GPKG", layer="affected_buildings")
            vector_paths["affected_buildings"] = bldg_path
            db.add(GeospatialOutput(
                id=f"out_bldg_{analysis.id}",
                analysis_id=analysis.id,
                product_type="affected_buildings",
                file_path=str(bldg_path),
                format="gpkg"
            ))

        if not affected_roads_gdf.empty:
            road_path = processed_dir / "affected_roads.gpkg"
            affected_roads_gdf.to_file(road_path, driver="GPKG", layer="affected_roads")
            vector_paths["affected_roads"] = road_path
            db.add(GeospatialOutput(
                id=f"out_road_{analysis.id}",
                analysis_id=analysis.id,
                product_type="affected_roads",
                file_path=str(road_path),
                format="gpkg"
            ))

        # 9. Compute Metric Areas
        area_metrics = calculate_impact_areas(
            class_raster, target_grid.transform, target_grid.crs, list(bounds), uncertainty_mask=high_uncert_mask
        )

        metrics_record = ImpactMetrics(
            id=f"met_{analysis.id}",
            analysis_id=analysis.id,
            total_observed_water_m2=area_metrics["total_water_m2"],
            preexisting_water_m2=area_metrics["preexisting_water_m2"],
            newly_flooded_m2=area_metrics["newly_flooded_m2"],
            receded_flooded_m2=area_metrics["receded_m2"],
            uncertain_water_m2=area_metrics["uncertain_water_m2"],
            total_buildings=building_stats["total_buildings"],
            affected_buildings=building_stats["affected_buildings"],
            uncertain_buildings=building_stats["uncertain_buildings"],
            total_road_meters=road_stats["total_road_meters"],
            affected_road_meters=road_stats["affected_road_meters"],
            uncertain_road_meters=0.0,
            metrics_breakdown_json={
                "area_metrics": area_metrics,
                "building_stats": building_stats,
                "road_stats": road_stats
            }
        )
        db.add(metrics_record)

        analysis.progress_pct = 85
        analysis.stage_message = "Generating evidence report & packaging"
        db.commit()

        # 10. Generate PDF Report
        event_dict = {
            "id": event.id,
            "name": event.name,
            "country": event.country,
            "bounds": bounds
        }
        obs_dicts = [
            {
                "sensor": o.sensor,
                "event_phase": o.event_phase,
                "observation_time": o.observation_time,
                "resolution_m": o.resolution_m
            }
            for o in observations
        ]
        summary_metrics_dict = {
            "total_water_km2": area_metrics["total_water_km2"],
            "preexisting_water_km2": area_metrics["preexisting_water_km2"],
            "newly_flooded_km2": area_metrics["newly_flooded_km2"],
            "receded_km2": area_metrics["receded_km2"],
            "uncertain_water_km2": area_metrics["uncertain_water_km2"],
            "total_buildings": building_stats["total_buildings"],
            "affected_buildings": building_stats["affected_buildings"],
            "total_road_km": road_stats["total_road_km"],
            "affected_road_km": road_stats["affected_road_km"]
        }

        pdf_path = generate_pdf_report(
            analysis_id=analysis.id,
            event_data=event_dict,
            metrics_data=summary_metrics_dict,
            observations=obs_dicts,
            analysis_config=config,
            output_path=settings.EXPORTS_DIR / f"flood_report_{analysis.id}.pdf"
        )
        db.add(GeospatialOutput(
            id=f"out_pdf_{analysis.id}",
            analysis_id=analysis.id,
            product_type="pdf_report",
            file_path=str(pdf_path),
            format="pdf"
        ))

        # 11. Create Evidence Package ZIP
        zip_path = create_evidence_package(
            analysis_id=analysis.id,
            event_data=event_dict,
            analysis_config=config,
            raster_paths=raster_paths,
            vector_paths=vector_paths,
            metrics_data=summary_metrics_dict,
            pdf_report_path=pdf_path
        )
        db.add(GeospatialOutput(
            id=f"out_zip_{analysis.id}",
            analysis_id=analysis.id,
            product_type="evidence_package",
            file_path=str(zip_path),
            format="zip"
        ))

        analysis.progress_pct = 100
        analysis.stage_message = "Analysis completed successfully"
        analysis.status = "completed"
        analysis.completed_at = datetime.datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.completed_at = datetime.datetime.utcnow()
            db.commit()
        raise e
    finally:
        db.close()
