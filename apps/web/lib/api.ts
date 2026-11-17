const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function fetchJson<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errMsg = `API error: ${res.status}`;
    try {
      const errData = await res.json();
      errMsg = errData.detail || errMsg;
    } catch (_) {}
    throw new Error(errMsg);
  }

  return res.json();
}

export const api = {
  getOverview: () => fetchJson<any>("/overview"),
  getEvents: () => fetchJson<any[]>("/events"),
  getEvent: (id: string) => fetchJson<any>(`/events/${id}`),
  createEvent: (data: any) =>
    fetchJson<any>("/events", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getObservations: (eventId: string) =>
    fetchJson<any[]>(`/events/${eventId}/observations`),
  triggerAnalysis: (eventId: string, config?: any) =>
    fetchJson<any>(`/events/${eventId}/analysis`, {
      method: "POST",
      body: JSON.stringify({ config }),
    }),
  getAnalysis: (analysisId: string) =>
    fetchJson<any>(`/analysis/${analysisId}`),
  getAnalysisMetrics: (analysisId: string) =>
    fetchJson<any>(`/analysis/${analysisId}/metrics`),
  getAnalysisOutputs: (analysisId: string) =>
    fetchJson<any[]>(`/analysis/${analysisId}/outputs`),
  getReviewRegions: (analysisId: string) =>
    fetchJson<any[]>(`/analysis/${analysisId}/review-regions`),
  submitReviewDecision: (regionId: string, decision: string, notes?: string) =>
    fetchJson<any>(`/review-regions/${regionId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, notes }),
    }),
  getReviewHistory: (eventId: string) =>
    fetchJson<any[]>(`/events/${eventId}/review-history`),
  getDownloadUrl: (analysisId: string) =>
    `${API_BASE}/reports/${analysisId}/download`,
  getPdfUrl: (analysisId: string) => `${API_BASE}/reports/${analysisId}/pdf`,
  getVectorGeoJsonUrl: (outputId: string) =>
    `${API_BASE}/vector/${outputId}/geojson`,
  getRasterPreviewUrl: (outputId: string) =>
    `${API_BASE}/tiles/raster/${outputId}/preview.png`,
};
