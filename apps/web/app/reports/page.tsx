"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function ReportsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getEvents()
      .then((data) => setEvents(data))
      .catch((err) => console.error("Failed to load events for reports:", err))
      .finally(() => setLoading(false));
  }, []);

  const analyzedEvents = events.filter((e) => e.latest_analysis_id);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 w-full space-y-8">
      <div className="border-b border-[#1e293b] pb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white">Evidence Reports & Packages</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-3xl leading-relaxed">
          Reproducible, georeferenced flood impact evidence dossiers. Each package contains human-readable PDF
          reports, Cloud-Optimized GeoTIFF rasters, GeoPackage vector layers, tabular impact metrics, and SHA-256
          integrity manifests.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-sm font-mono text-slate-500">Loading dossiers...</div>
      ) : analyzedEvents.length > 0 ? (
        <div className="divide-y divide-[#1e293b] bg-[#0f172a] border border-[#1e293b] rounded-lg overflow-hidden">
          {analyzedEvents.map((ev) => (
            <div key={ev.id} className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-mono text-slate-400">
                  {ev.country || "Global"} &bull; {ev.id}
                </span>
                <h3 className="text-base font-semibold text-white tracking-tight mt-0.5">{ev.name}</h3>
                <span className="text-xs text-slate-500 font-mono block mt-1">
                  Analysis ID: {ev.latest_analysis_id}
                </span>
              </div>

              <div className="flex items-center space-x-3">
                <a
                  href={api.getPdfUrl(ev.latest_analysis_id)}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-[#161f30] hover:bg-[#1f2c44] border border-[#233149] rounded text-xs font-medium text-slate-200 transition-colors"
                >
                  View PDF Report
                </a>
                <a
                  href={api.getDownloadUrl(ev.latest_analysis_id)}
                  download
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium transition-colors shadow-sm"
                >
                  Download Evidence ZIP
                </a>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-16 text-center bg-[#0f172a] border border-[#1e293b] rounded-lg space-y-3">
          <p className="text-sm text-slate-300 font-medium">No completed analyses yet.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Run an analysis on any flood event to automatically generate PDF reports and reproducible evidence ZIP packages.
          </p>
          <Link
            href="/events"
            className="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white rounded transition-colors"
          >
            Go to Events Catalog
          </Link>
        </div>
      )}
    </div>
  );
}
