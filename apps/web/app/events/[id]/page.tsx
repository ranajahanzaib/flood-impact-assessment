"use client";

import { api } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

export default function EventWorkspacePage() {
  const params = useParams();
  const eventId = params.id as string;

  const [event, setEvent] = useState<any>(null);
  const [observations, setObservations] = useState<any[]>([]);
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [outputs, setOutputs] = useState<any[]>([]);
  const [reviewRegions, setReviewRegions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Map layer controls
  const [activeLayer, setActiveLayer] = useState<string>("classification");
  const [showBuildings, setShowBuildings] = useState(true);
  const [showRoads, setShowRoads] = useState(true);
  const [selectedPhase, setSelectedPhase] = useState<string>("during");
  const [inspectorData, setInspectorData] = useState<any>(null);

  // Manual Review Dialog
  const [activeReviewRegion, setActiveReviewRegion] = useState<any>(null);
  const [reviewerNotes, setReviewerNotes] = useState("");

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);

  const loadEventData = useCallback(async () => {
    setLoading(true);
    try {
      const ev = await api.getEvent(eventId);
      setEvent(ev);

      const obs = await api.getObservations(eventId);
      setObservations(obs);

      if (ev.latest_analysis_id) {
        const anl = await api.getAnalysis(ev.latest_analysis_id);
        setActiveAnalysis(anl);
        if (anl.status === "completed") {
          const m = await api.getAnalysisMetrics(anl.id);
          setMetrics(m);
          const outs = await api.getAnalysisOutputs(anl.id);
          setOutputs(outs);
          const revs = await api.getReviewRegions(anl.id);
          setReviewRegions(revs);
        }
      }
    } catch (err) {
      console.error("Failed to load event data:", err);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    loadEventData();
  }, [loadEventData]);

  const handleRunAnalysis = async (method: string = "baseline") => {
    setAnalyzing(true);
    try {
      const anl = await api.triggerAnalysis(eventId, {
        method,
        output_crs: "EPSG:4326",
        output_resolution_m: 10.0,
        probability_threshold: 0.5,
      });
      setActiveAnalysis(anl);

      // Poll until completed
      const interval = setInterval(async () => {
        const updated = await api.getAnalysis(anl.id);
        setActiveAnalysis(updated);
        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(interval);
          setAnalyzing(false);
          loadEventData();
        }
      }, 2000);
    } catch (err: any) {
      alert(`Analysis trigger failed: ${err.message}`);
      setAnalyzing(false);
    }
  };

  const handleReviewDecision = async (decision: string) => {
    if (!activeReviewRegion) return;
    try {
      await api.submitReviewDecision(
        activeReviewRegion.id,
        decision,
        reviewerNotes,
      );
      setActiveReviewRegion(null);
      setReviewerNotes("");
      if (activeAnalysis) {
        const revs = await api.getReviewRegions(activeAnalysis.id);
        setReviewRegions(revs);
      }
    } catch (err: any) {
      alert(`Review decision failed: ${err.message}`);
    }
  };

  // Find preview images for active analysis
  const classificationOutput = outputs.find(
    (o) => o.product_type === "flood_classification",
  );
  const newInundationOutput = outputs.find(
    (o) => o.product_type === "new_inundation",
  );
  const persistenceOutput = outputs.find(
    (o) => o.product_type === "persistence",
  );
  const uncertaintyOutput = outputs.find(
    (o) => o.product_type === "uncertainty",
  );

  return (
    <div className="flex-1 flex flex-col h-[calc(100vh-57px)] overflow-hidden">
      {/* Top Event Workspace Header */}
      <div className="bg-[#0c1220] border-b border-[#1e293b] px-6 py-3 flex flex-wrap items-center justify-between gap-4 z-20">
        <div className="flex items-center space-x-4">
          <Link
            href="/events"
            className="text-slate-400 hover:text-white text-xs font-mono"
          >
            &larr; Events
          </Link>
          <div className="h-4 w-px bg-slate-700"></div>
          <div>
            <h1 className="text-sm font-bold text-white flex items-center gap-2">
              {event?.name || "Loading..."}
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1e293b] text-slate-300">
                {event?.id}
              </span>
            </h1>
            <span className="text-[11px] text-slate-400 font-mono">
              {event?.country || "Global"} &bull; {observations.length}{" "}
              Registered Observations
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {activeAnalysis?.status === "completed" && (
            <>
              <a
                href={api.getPdfUrl(activeAnalysis.id)}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-[#161f30] hover:bg-[#1f2c44] border border-[#233149] rounded text-xs font-medium text-slate-200 transition-colors flex items-center gap-1.5"
              >
                <span>PDF Evidence Report</span>
              </a>
              <a
                href={api.getDownloadUrl(activeAnalysis.id)}
                download
                className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-sky-400 border border-blue-500/30 rounded text-xs font-medium transition-colors"
              >
                Download Evidence ZIP
              </a>
            </>
          )}

          <button
            onClick={() => handleRunAnalysis("baseline")}
            disabled={analyzing || observations.length === 0}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded text-xs font-medium shadow-sm transition-colors"
          >
            {analyzing
              ? `Processing (${activeAnalysis?.progress_pct || 0}%)...`
              : "Run Multi-Sensor Analysis"}
          </button>
        </div>
      </div>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Interactive Map & Temporal Controls */}
        <div className="flex-1 flex flex-col relative bg-[#070b12]">
          {/* Map Surface */}
          <div className="flex-1 relative flex items-center justify-center overflow-hidden">
            {activeAnalysis?.status === "completed" ? (
              <div className="w-full h-full relative flex items-center justify-center p-4">
                {/* Simulated Georeferenced Raster Render Viewer */}
                <div className="relative max-w-full max-h-full border border-[#1e293b] rounded-lg overflow-hidden shadow-2xl bg-[#090d16] flex items-center justify-center">
                  {activeLayer === "classification" && classificationOutput && (
                    <img
                      src={api.getRasterPreviewUrl(classificationOutput.id)}
                      alt="Flood Classification"
                      className="max-h-[60vh] object-contain"
                    />
                  )}
                  {activeLayer === "new_inundation" && newInundationOutput && (
                    <img
                      src={api.getRasterPreviewUrl(newInundationOutput.id)}
                      alt="Newly Inundated Land"
                      className="max-h-[60vh] object-contain"
                    />
                  )}
                  {activeLayer === "persistence" && persistenceOutput && (
                    <img
                      src={api.getRasterPreviewUrl(persistenceOutput.id)}
                      alt="Temporal Persistence"
                      className="max-h-[60vh] object-contain"
                    />
                  )}
                  {activeLayer === "uncertainty" && uncertaintyOutput && (
                    <img
                      src={api.getRasterPreviewUrl(uncertaintyOutput.id)}
                      alt="Uncertainty Heatmap"
                      className="max-h-[60vh] object-contain"
                    />
                  )}

                  {/* On-Map Inspection Overlay Click Simulation */}
                  <div
                    onClick={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      const x = e.clientX - rect.left;
                      const y = e.clientY - rect.top;
                      setInspectorData({
                        lat:
                          (event?.bounds_geojson?.[1] || 50.5) +
                          (y / rect.height) * 0.1,
                        lon:
                          (event?.bounds_geojson?.[0] || 7.0) +
                          (x / rect.width) * 0.1,
                        classification:
                          activeLayer === "classification"
                            ? "Newly Inundated Land"
                            : activeLayer,
                        confidence: 0.94,
                        sensor: "Sentinel-1 SAR / Sentinel-2 Composite",
                        model: activeAnalysis.config_json?.method || "baseline",
                        uncertainty: 0.12,
                      });
                    }}
                    className="absolute inset-0 cursor-crosshair"
                    title="Click map location to inspect geospatial evidence"
                  />
                </div>

                {/* Floating Inspector Tooltip */}
                {inspectorData && (
                  <div className="absolute bottom-6 left-6 z-30 bg-[#0f172a]/95 border border-[#1e293b] rounded-lg p-3 text-xs font-mono text-slate-300 shadow-xl backdrop-blur max-w-xs space-y-1">
                    <div className="flex items-center justify-between font-bold text-white mb-1 border-b border-slate-700 pb-1">
                      <span>Evidence Inspection</span>
                      <button
                        onClick={() => setInspectorData(null)}
                        className="text-slate-400 hover:text-white"
                      >
                        &times;
                      </button>
                    </div>
                    <div>
                      Lat/Lon: {inspectorData.lat.toFixed(4)},{" "}
                      {inspectorData.lon.toFixed(4)}
                    </div>
                    <div>
                      Class:{" "}
                      <span className="text-rose-400 font-bold">
                        {inspectorData.classification}
                      </span>
                    </div>
                    <div>Sensor: {inspectorData.sensor}</div>
                    <div>Engine: {inspectorData.model}</div>
                    <div>Uncertainty: {inspectorData.uncertainty} (Low)</div>
                  </div>
                )}
              </div>
            ) : analyzing ? (
              <div className="text-center space-y-3 p-8">
                <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <div className="text-sm font-semibold text-white">
                  {activeAnalysis?.stage_message ||
                    "Reconstructing flood extent..."}
                </div>
                <div className="text-xs font-mono text-slate-400">
                  Stage Progress: {activeAnalysis?.progress_pct || 0}%
                </div>
              </div>
            ) : (
              <div className="text-center space-y-3 p-8 max-w-md">
                <div className="w-12 h-12 rounded-full bg-[#161f30] flex items-center justify-center mx-auto text-blue-400">
                  🛰️
                </div>
                <h3 className="text-base font-semibold text-white">
                  Observation Grid Ready
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {observations.length > 0
                    ? `${observations.length} observations registered for this flood event. Click 'Run Multi-Sensor Analysis' to reconstruct extent and measure infrastructure exposure.`
                    : "No satellite observations registered yet. Add Sentinel-1 or Sentinel-2 scenes to begin reconstruction."}
                </p>
                {observations.length > 0 && (
                  <button
                    onClick={() => handleRunAnalysis("baseline")}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium shadow-sm transition-colors"
                  >
                    Start Reconstruction
                  </button>
                )}
              </div>
            )}

            {/* Floating Layer Selector Bar */}
            {activeAnalysis?.status === "completed" && (
              <div className="absolute top-4 left-4 z-20 bg-[#0f172a]/90 backdrop-blur border border-[#1e293b] rounded-md p-1.5 flex items-center space-x-1 shadow-lg text-xs font-medium">
                <button
                  onClick={() => setActiveLayer("classification")}
                  className={`px-3 py-1 rounded transition-colors ${
                    activeLayer === "classification"
                      ? "bg-blue-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Full Classification
                </button>
                <button
                  onClick={() => setActiveLayer("new_inundation")}
                  className={`px-3 py-1 rounded transition-colors ${
                    activeLayer === "new_inundation"
                      ? "bg-rose-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Newly Inundated
                </button>
                <button
                  onClick={() => setActiveLayer("persistence")}
                  className={`px-3 py-1 rounded transition-colors ${
                    activeLayer === "persistence"
                      ? "bg-indigo-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Persistence
                </button>
                <button
                  onClick={() => setActiveLayer("uncertainty")}
                  className={`px-3 py-1 rounded transition-colors ${
                    activeLayer === "uncertainty"
                      ? "bg-amber-600 text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Uncertainty
                </button>
              </div>
            )}

            {/* Cartographic Legend */}
            {activeAnalysis?.status === "completed" && (
              <div className="absolute top-4 right-4 z-20 bg-[#0f172a]/90 backdrop-blur border border-[#1e293b] rounded-md p-3 shadow-lg text-[11px] font-mono space-y-1.5">
                <span className="font-bold text-white block uppercase tracking-wider text-[10px] mb-1">
                  Layer Legend
                </span>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-sky-500"></span>
                  <span className="text-slate-300">Pre-Existing Water</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-red-500"></span>
                  <span className="text-slate-300">Newly Inundated Land</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-emerald-500"></span>
                  <span className="text-slate-300">Observed Recession</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded bg-amber-500"></span>
                  <span className="text-slate-300">Uncertain / Flagged</span>
                </div>
              </div>
            )}
          </div>

          {/* Temporal Phase Selector Timeline */}
          <div className="h-16 bg-[#0c1220] border-t border-[#1e293b] px-6 flex items-center justify-between text-xs z-20">
            <div className="flex items-center space-x-6">
              <span className="text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                Observation Timeline
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setSelectedPhase("before")}
                  className={`px-3 py-1 rounded font-mono text-xs border ${
                    selectedPhase === "before"
                      ? "bg-[#1e293b] border-sky-500 text-sky-400"
                      : "bg-[#161f30] border-transparent text-slate-400 hover:text-white"
                  }`}
                >
                  Phase 1: Before (Baseline)
                </button>
                <span className="text-slate-600">&rarr;</span>
                <button
                  onClick={() => setSelectedPhase("during")}
                  className={`px-3 py-1 rounded font-mono text-xs border ${
                    selectedPhase === "during"
                      ? "bg-[#1e293b] border-rose-500 text-rose-400"
                      : "bg-[#161f30] border-transparent text-slate-400 hover:text-white"
                  }`}
                >
                  Phase 2: During (Peak Inundation)
                </button>
                <span className="text-slate-600">&rarr;</span>
                <button
                  onClick={() => setSelectedPhase("after")}
                  className={`px-3 py-1 rounded font-mono text-xs border ${
                    selectedPhase === "after"
                      ? "bg-[#1e293b] border-emerald-500 text-emerald-400"
                      : "bg-[#161f30] border-transparent text-slate-400 hover:text-white"
                  }`}
                >
                  Phase 3: After (Recession)
                </button>
              </div>
            </div>

            <div className="text-[11px] font-mono text-slate-400">
              CRS: {activeAnalysis?.config_json?.output_crs || "EPSG:4326"}{" "}
              &bull; Res: 10m
            </div>
          </div>
        </div>

        {/* Right Side: Impact Metrics, Infrastructure & Manual Review */}
        <div className="w-80 md:w-96 bg-[#0f172a] border-l border-[#1e293b] flex flex-col h-full overflow-y-auto">
          {/* Metrics Section */}
          <div className="p-5 border-b border-[#1e293b] space-y-4">
            <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Impact Evidence Metrics
            </h2>

            {metrics ? (
              <div className="space-y-3">
                <div className="bg-[#161f30] border border-[#233149] rounded p-3">
                  <span className="text-[11px] text-slate-400 block">
                    Newly Inundated Land
                  </span>
                  <span className="text-xl font-bold text-rose-400">
                    {(metrics.newly_flooded_m2 / 1e6).toFixed(2)} km²
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono block mt-0.5">
                    {(metrics.newly_flooded_m2 / 10000).toLocaleString(
                      undefined,
                      { maximumFractionDigits: 1 },
                    )}{" "}
                    ha
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-[#161f30] p-2.5 rounded border border-[#233149]">
                    <span className="text-[10px] text-slate-400 block">
                      Pre-Existing Water
                    </span>
                    <span className="font-bold text-slate-200">
                      {(metrics.preexisting_water_m2 / 1e6).toFixed(2)} km²
                    </span>
                  </div>
                  <div className="bg-[#161f30] p-2.5 rounded border border-[#233149]">
                    <span className="text-[10px] text-slate-400 block">
                      Observed Recession
                    </span>
                    <span className="font-bold text-emerald-400">
                      {(metrics.receded_flooded_m2 / 1e6).toFixed(2)} km²
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-[#161f30] p-2.5 rounded border border-[#233149]">
                    <span className="text-[10px] text-slate-400 block">
                      Affected Buildings
                    </span>
                    <span className="font-bold text-amber-400">
                      {metrics.affected_buildings.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      of {metrics.total_buildings}
                    </span>
                  </div>
                  <div className="bg-[#161f30] p-2.5 rounded border border-[#233149]">
                    <span className="text-[10px] text-slate-400 block">
                      Inundated Roads
                    </span>
                    <span className="font-bold text-sky-400">
                      {(metrics.affected_road_meters / 1000).toFixed(2)} km
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      of {(metrics.total_road_meters / 1000).toFixed(1)} km
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-500 bg-[#161f30] rounded border border-[#233149]">
                Metrics will be calculated once the analysis pipeline runs.
              </div>
            )}
          </div>

          {/* Manual Review Regions Section */}
          <div className="p-5 border-b border-[#1e293b] space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
                Manual Verification Queue
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300">
                {reviewRegions.length} Regions
              </span>
            </div>

            {reviewRegions.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {reviewRegions.map((reg) => (
                  <div
                    key={reg.id}
                    className="p-2.5 rounded bg-[#161f30] border border-[#233149] hover:border-slate-600 transition-colors cursor-pointer text-xs space-y-1"
                    onClick={() => setActiveReviewRegion(reg)}
                  >
                    <div className="flex items-center justify-between font-medium">
                      <span className="text-slate-200">
                        Flag: {reg.flag_type}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                          reg.status === "pending"
                            ? "bg-amber-950 text-amber-300"
                            : reg.status === "confirmed_flood"
                              ? "bg-rose-950 text-rose-300"
                              : "bg-emerald-950 text-emerald-300"
                        }`}
                      >
                        {reg.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2">
                      {reg.reason}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[11px] text-slate-500 bg-[#161f30] p-3 rounded">
                No high-uncertainty regions requiring manual verification.
              </div>
            )}
          </div>

          {/* Observations List */}
          <div className="p-5 space-y-3 flex-1">
            <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Observations List ({observations.length})
            </h2>
            <div className="space-y-2">
              {observations.map((obs) => (
                <div
                  key={obs.id}
                  className="p-2.5 bg-[#161f30] rounded border border-[#233149] text-xs"
                >
                  <div className="flex items-center justify-between font-mono text-[11px] mb-1">
                    <span className="font-bold text-sky-400 uppercase">
                      {obs.sensor}
                    </span>
                    <span className="text-slate-400 capitalize">
                      {obs.event_phase}
                    </span>
                  </div>
                  <div className="text-slate-300 text-[11px]">
                    {new Date(obs.observation_time).toLocaleString()}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono mt-1">
                    Res: {obs.resolution_m || 10}m &bull; CRS: {obs.crs}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Manual Review Modal Dialog */}
      {activeReviewRegion && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div>
              <h3 className="text-base font-bold text-white">
                Manual Analyst Verification
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Region flagged due to sensor disagreement or high entropy.
              </p>
            </div>

            <div className="p-3 bg-[#161f30] rounded border border-[#233149] text-xs font-mono space-y-1">
              <div>Region ID: {activeReviewRegion.id}</div>
              <div>
                Flag Type:{" "}
                <span className="text-amber-400">
                  {activeReviewRegion.flag_type}
                </span>
              </div>
              <div className="text-slate-300 mt-2">
                {activeReviewRegion.reason}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Analyst Notes / Rationale
              </label>
              <textarea
                rows={2}
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                placeholder="Observed cloud shadow attenuation, confirmed seasonal wetland..."
                className="w-full bg-[#161f30] border border-[#233149] rounded p-2 text-xs text-white focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setActiveReviewRegion(null)}
                className="px-3 py-1.5 bg-[#1e293b] text-slate-300 text-xs rounded hover:bg-[#283852]"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => handleReviewDecision("confirmed_dry")}
                className="px-3 py-1.5 bg-slate-700 text-white text-xs rounded hover:bg-slate-600"
              >
                Confirm Dry
              </button>
              <button
                type="button"
                onClick={() => handleReviewDecision("confirmed_flood")}
                className="px-3 py-1.5 bg-rose-600 text-white text-xs rounded hover:bg-rose-500 font-medium"
              >
                Confirm Inundation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
