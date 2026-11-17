"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const PRESET_EVENTS = [
  {
    id: "EMSR548_GER",
    name: "2021 Western Germany Flash Floods (Ahr Valley)",
    country: "Germany",
    description: "Extreme precipitation and catastrophic flash flooding along the Ahr and Erft rivers.",
    bounds: [6.85, 50.45, 7.25, 50.65],
  },
  {
    id: "EMSR590_PAK",
    name: "2022 Sindh Monsoon Floods (Indus River Basin)",
    country: "Pakistan",
    description: "Historic monsoon rainfall causing extensive prolonged inundation across the Sindh province.",
    bounds: [67.80, 26.20, 68.30, 26.70],
  },
  {
    id: "EMSR298_GRC",
    name: "Attica Coastal Inundation Event",
    country: "Greece",
    description: "Severe Mediterranean storm surge and coastal flooding.",
    bounds: [23.80, 38.00, 24.10, 38.25],
  },
];

export default function NewEventPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [description, setDescription] = useState("");
  const [bounds, setBounds] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectPreset = (preset: any) => {
    setName(preset.name);
    setCountry(preset.country);
    setDescription(preset.description);
    setBounds(JSON.stringify(preset.bounds));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    setError(null);

    let parsedBounds = null;
    if (bounds.trim()) {
      try {
        parsedBounds = JSON.parse(bounds);
      } catch (err) {
        setError("Invalid JSON format for bounding box. Expected [min_lon, min_lat, max_lon, max_lat]");
        setLoading(false);
        return;
      }
    }

    try {
      const created = await api.createEvent({
        name,
        country: country || undefined,
        description: description || undefined,
        bounds_geojson: parsedBounds,
      });
      router.push(`/events/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create event");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 w-full space-y-8">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Register Flood Event</h1>
        <p className="text-xs text-slate-400 mt-1">
          Define an area of interest and initialize a multi-temporal flood impact evidence dossier.
        </p>
      </div>

      {/* Preset Benchmark Quick Select */}
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-5">
        <span className="text-xs font-mono text-slate-400 uppercase tracking-wider block mb-3">
          Quick Load ImpactMesh-Flood Benchmark Events
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PRESET_EVENTS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handleSelectPreset(p)}
              className="text-left p-3 rounded bg-[#161f30] hover:bg-[#1f2c44] border border-[#233149] transition-colors"
            >
              <span className="text-xs font-semibold text-white block truncate">{p.name}</span>
              <span className="text-[10px] text-slate-400 font-mono mt-1 block">
                {p.country} &bull; {p.id}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-6 space-y-5">
        {error && (
          <div className="p-3 bg-red-950/40 border border-red-800 text-red-200 text-xs rounded">
            {error}
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Event Name *
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. 2021 Ahr Valley Flash Floods"
            className="w-full bg-[#161f30] border border-[#233149] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Country / Region
          </label>
          <input
            type="text"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="e.g. Germany"
            className="w-full bg-[#161f30] border border-[#233149] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Description & Context
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Meteorological cause, river catchment details, or affected regions..."
            className="w-full bg-[#161f30] border border-[#233149] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Geographic Bounding Box [min_lon, min_lat, max_lon, max_lat] (JSON)
          </label>
          <input
            type="text"
            value={bounds}
            onChange={(e) => setBounds(e.target.value)}
            placeholder="[6.85, 50.45, 7.25, 50.65]"
            className="w-full bg-[#161f30] border border-[#233149] rounded px-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="pt-2 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => router.back()}
            className="px-4 py-2 bg-[#161f30] hover:bg-[#1f2c44] text-xs font-medium text-slate-300 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-medium text-white rounded transition-colors shadow-sm"
          >
            {loading ? "Registering..." : "Create Event Dossier"}
          </button>
        </div>
      </form>
    </div>
  );
}
