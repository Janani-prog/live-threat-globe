export interface CountBucket {
  key: string;
  count: number;
}

export interface StatsSummary {
  total_events: number;
  top_countries: CountBucket[];
  top_asns: CountBucket[];
  category_breakdown: CountBucket[];
  cloudflare_top_origin_countries: Record<string, unknown>[] | null;
}

export interface TimeseriesPoint {
  bucket: string;
  count: number;
}

export interface TimeseriesOut {
  points: TimeseriesPoint[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchStatsSummary(): Promise<StatsSummary | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stats/summary`);
    if (!res.ok) return null;
    return (await res.json()) as StatsSummary;
  } catch {
    return null;
  }
}

export async function fetchStatsTimeseries(minutes = 60): Promise<TimeseriesOut | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stats/timeseries?minutes=${minutes}`);
    if (!res.ok) return null;
    return (await res.json()) as TimeseriesOut;
  } catch {
    return null;
  }
}
