"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function EventsListPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getEvents()
      .then((data) => setEvents(data))
      .catch((err) => console.error("Failed to load events:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 w-full space-y-6">
      <div className="flex items-center justify-between border-b border-[#1e293b] pb-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Flood Events Catalog</h1>
          <p className="text-xs text-slate-400 mt-1">
            Registered flood events, satellite observation feeds, and reconstruction status.
          </p>
        </div>
        <Link
          href="/events/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-md text-xs font-medium text-white transition-colors"
        >
          + Register Event
        </Link>
      </div>

      {loading ? (
        <div className="p-12 text-center text-sm font-mono text-slate-500">Loading catalog...</div>
      ) : events.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map((ev) => (
            <div
              key={ev.id}
              className="bg-[#0f172a] border border-[#1e293b] hover:border-slate-700 rounded-lg p-5 flex flex-col justify-between transition-colors shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                  <span>{ev.country || "Global"}</span>
                  <span className="px-2 py-0.5 rounded bg-[#1e293b] text-slate-300">
                    {ev.observation_count} obs
                  </span>
                </div>
                <h2 className="text-base font-semibold text-white tracking-tight mb-1">
                  {ev.name}
                </h2>
                <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">
                  {ev.description || "Multi-sensor flood observation dossier."}
                </p>
              </div>

              <div className="pt-4 border-t border-[#1e293b] flex items-center justify-between">
                <span className="text-[11px] text-slate-500 font-mono">
                  {new Date(ev.created_at).toLocaleDateString()}
                </span>
                <Link
                  href={`/events/${ev.id}`}
                  className="px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-sky-400 border border-blue-500/30 rounded text-xs font-medium transition-colors"
                >
                  Open Workspace &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-16 text-center bg-[#0f172a] border border-[#1e293b] rounded-lg space-y-3">
          <p className="text-sm text-slate-300 font-medium">No flood events registered yet.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            You can create a custom flood event or load one of the benchmark events from the ImpactMesh-Flood dataset.
          </p>
          <Link
            href="/events/new"
            className="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white rounded transition-colors"
          >
            Create New Event
          </Link>
        </div>
      )}
    </div>
  );
}
