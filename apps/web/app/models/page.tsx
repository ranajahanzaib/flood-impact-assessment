export default function ModelsPage() {
  const models = [
    {
      id: "baseline-radar-optical-v1",
      name: "Multi-Sensor Physical Baseline",
      type: "Heuristic Physical Indices & Thresholding",
      sensors: ["Sentinel-1 SAR", "Sentinel-2 Optical", "DEM"],
      bands: "VV, VH, NDWI, MNDWI, Slope",
      license: "MIT",
      description:
        "Deterministic physical sensor detection using Lee speckle filtering, dual-polarization SAR backscatter thresholding, optical NDWI/MNDWI indices, cloud/shadow masks, and topographic slope constraints. Operates out-of-the-box with zero foundation model downloads.",
      status: "Active / Standalone Ready",
    },
    {
      id: "ibm-nasa-geospatial/Prithvi-EO-2.0-300M",
      name: "Prithvi-EO-2.0-300M Flood Adapter",
      type: "Spatio-Temporal Vision Transformer (ViT)",
      sensors: ["Sentinel-2 Optical / HLS"],
      bands: "B02 (Blue), B03 (Green), B04 (Red), B8A (Narrow NIR), B11 (SWIR1), B12 (SWIR2)",
      license: "Apache 2.0",
      description:
        "Joint IBM-NASA Earth Observation foundation model trained on HLS archive. Processes temporal sequences with 3D patch and spatiotemporal positional embeddings. Downstream segmentation head produces georeferenced flood masks.",
      status: "Adapter Integrated",
    },
    {
      id: "made-with-clay/Clay",
      name: "Clay Multi-Sensor Foundation Model",
      type: "Tokenized Multi-Sensor ViT",
      sensors: ["Sentinel-1 SAR", "Sentinel-2 Optical", "DEM", "Landsat"],
      bands: "10-Channel Normalized Sensor Composite",
      license: "Apache 2.0",
      description:
        "Open-source multimodal foundation model designed specifically for Earth observation. Integrates diverse spectral and radar bands into unified representation space for downstream environmental hazards.",
      status: "Adapter Integrated",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 w-full space-y-8">
      <div className="border-b border-[#1e293b] pb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white">Detection Models & Adapters</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-3xl leading-relaxed">
          The platform decouples geospatial processing from specific machine learning backbones through a unified
          Model Adapter abstraction. Foundation models complement, rather than blindly replace, sensor-specific
          physical detection.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {models.map((m) => (
          <div
            key={m.id}
            className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-6 flex flex-col justify-between space-y-4 shadow-sm"
          >
            <div>
              <div className="flex items-center justify-between text-xs font-mono mb-2">
                <span className="text-blue-400 font-bold">{m.license}</span>
                <span className="px-2 py-0.5 rounded bg-[#161f30] text-emerald-400 border border-[#233149] text-[10px]">
                  {m.status}
                </span>
              </div>
              <h3 className="text-base font-semibold text-white tracking-tight">{m.name}</h3>
              <span className="text-[11px] font-mono text-slate-500 block mt-0.5">{m.id}</span>
              <p className="text-xs text-slate-300 mt-3 leading-relaxed">{m.description}</p>

              <div className="mt-4 pt-3 border-t border-[#1e293b] space-y-2 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Sensors</span>
                  <span className="text-slate-300">{m.sensors.join(", ")}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Input Channels</span>
                  <span className="text-slate-300 text-[11px]">{m.bands}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
