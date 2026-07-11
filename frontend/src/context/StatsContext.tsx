import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  fetchStatsSummary,
  fetchStatsTimeseries,
  type StatsSummary,
  type TimeseriesOut,
} from "../lib/stats";

// Stats are polled, not pushed over the WebSocket — they're aggregate
// rollups, not per-event data, and don't need sub-30s freshness (Technical
// Architecture doc section 6).
const POLL_INTERVAL_MS = 30000;

interface StatsValue {
  summary: StatsSummary | null;
  timeseries: TimeseriesOut | null;
}

const StatsContext = createContext<StatsValue>({ summary: null, timeseries: null });

export function StatsProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesOut | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      const [s, t] = await Promise.all([fetchStatsSummary(), fetchStatsTimeseries()]);
      if (cancelled) return;
      if (s) setSummary(s);
      if (t) setTimeseries(t);
    }

    poll();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return <StatsContext.Provider value={{ summary, timeseries }}>{children}</StatsContext.Provider>;
}

export function useStats(): StatsValue {
  return useContext(StatsContext);
}
