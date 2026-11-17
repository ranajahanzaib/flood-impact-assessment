"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function OverviewPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getOverview()
      .then((data) => setStats(data))
      .catch((err) => console.error("Failed to load overview stats:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 w-full space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e293b] pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Operational Overview
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Multi-sensor Earth observation evidence, inundation persistence, and infrastructure exposure.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/datasets"
            className="px-4 py-2 bg-[#161f30] hover:bg-[#1f2c44] border border-[#233149] rounded-md text-xs font-medium text-slate-300 transition-colors"
          >
            Explore Datasets
          </Link>
          <Link
            href="/events/new"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-md text-xs font-medium text-white transition-colors shadow-sm"
          >
            + Start New Reconstruction
          </Link>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-5">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
            Analyzed Events
          </span>
          <span className="text-2xl font-bold text-white mt-2 block">
            {loading ? "..." : stats?.total_events || 0}
          </span>
          <span className="text-xs text-slate-500 mt-1 block">Active event dossiers</span>
        </div>

        <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-5">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
            Newly Flooded Land
          </span>
          <span className="text-2xl font-bold text-rose-400 mt-2 block">
            {loading ? "..." : `${stats?.total_newly_flooded_km2 || 0} km²`}
          </span>
          <span className="text-xs text-slate-500 mt-1 block">Excludes pre-existing water</span>
        </div>

        <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-5">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
            Affected Buildings
          </span>
          <span className="text-2xl font-bold text-amber-400 mt-2 block">
            {loading ? "..." : (stats?.total_affected_buildings || 0).toLocaleString()}
          </span>
          <span className="text-xs text-slate-500 mt-1 block">Intersecting inundation</span>
        </div>

        <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-5">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
            Inundated Roads
          </span>
          <span className="text-2xl font-bold text-sky-400 mt-2 block">
            {loading ? "..." : `${stats?.total_affected_road_km || 0} km`}
          </span>
          <span className="text-xs text-slate-500 mt-1 block">Segment line intersections</span>
        </div>

        <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-5">
          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
            Manual Reviews
          </span>
          <span className="text-2xl font-bold text-purple-400 mt-2 block">
            {loading ? "..." : stats?.pending_manual_reviews || 0}
          </span>
          <span className="text-xs text-slate-500 mt-1 block">High uncertainty regions</span>
        </div>
      </div>

      {/* Workflow Explanation Banner */}
      <div className="bg-[#0d1424] border border-[#1b263b] rounded-lg p-6">
        <h2 className="text-sm font-semibold text-white tracking-wide uppercase font-mono mb-3">
          Evidence Reconstruction Architecture
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="bg-[#111a2e] p-4 rounded border border-[#1e2b46]">
            <span className="text-blue-400 font-mono font-bold block mb-1">01 / Observation Ingestion</span>
            <p className="text-slate-300 leading-relaxed">
              Accepts Sentinel-1 SAR and Sentinel-2 optical scenes from before, during, and after flood phases.
            </p>
          </div>
          <div className="bg-[#111a2e] p-4 rounded border border-[#1e2b46]">
            <span className="text-blue-400 font-mono font-bold block mb-1">02 / Common Grid Alignment</span>
            <p className="text-slate-300 leading-relaxed">
              Re-projects heterogeneous inputs to an aligned spatial grid with rigorous NoData and cloud mask propagation.
            </p>
          </div>
          <div className="bg-[#111a2e] p-4 rounded border border-[#1e2b46]">
            <span className="text-blue-400 font-mono font-bold block mb-1">03 / Pre-Existing Water Separation</span>
            <p className="text-slate-300 leading-relaxed">
              Distinguishes permanent baseline water bodies from newly inundated land using pre-event observations.
            </p>
          </div>
          <div className="bg-[#111a2e] p-4 rounded border border-[#1e2b46]">
            <span className="text-blue-400 font-mono font-bold block mb-1">04 / Infrastructure & Provenance</span>
            <p className="text-slate-300 leading-relaxed">
              Overlays building footprints and road networks, measures exposure, flags uncertainty, and produces SHA-256 evidence packages.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Events Table */}
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-[#1e293b] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Recent Flood Analyses</h2>
          <Link href="/events" className="text-xs font-mono text-sky-400 hover:text-sky-300">
            View All Events &rarr;
          </Link>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500 font-mono">Loading events...</div>
        ) : stats?.recent_events?.length > 0 ? (
          <div className="divide-y divide-[#1e293b]">
            {stats.recent_events.map((ev: any) => (
              <div
                key={ev.id}
                className="px-6 py-4 flex items-center justify-between hover:bg-[#141e33] transition-colors"
              >
                <div>
                  <Link
                    href={`/events/${ev.id}`}
                    className="font-medium text-white hover:text-sky-400 text-sm block"
                  >
                    {ev.name}
                  </Link>
                  <span className="text-xs text-slate-400 font-mono">
                    ID: {ev.id} &bull; {ev.country || "Global"}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-500 font-mono">
                    {new Date(ev.created_at).toLocaleDateString()}
                  </span>
                  <Link
                    href={`/events/${ev.id}`}
                    className="px-3 py-1 bg-[#1e293b] hover:bg-[#283852] text-xs font-medium text-slate-200 rounded transition-colors"
                  >
                    Open Workspace
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center space-y-3">
            <p className="text-sm text-slate-400">No flood events analyzed yet.</p>
            <p className="text-xs text-slate-500">
              Create a new event or load a sample event from the ImpactMesh-Flood dataset to start.
            </p>
            <Link
              href="/events/new"
              className="inline-block mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white rounded-md transition-colors"
            >
              + Create First Event
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
