import { useThreatFeed } from "../context/ThreatFeedContext";
import { useStats } from "../context/StatsContext";
import type { View } from "../lib/view";

// Adapts the Stitch mockup's top nav bar structure (flex justify-between,
// backdrop-blur, border-b) but drops the "CYBERTHREAT LIVE MAP" wordmark
// (CLAUDE.md: no product name/logo in the deployed UI) and the unrelated
// STATISTICS/DATA SOURCES/BUZZ/WIDGET links, keeping only the two views
// this app actually has, plus a live stat strip (PRD F6).
const TABS: { key: View; label: string }[] = [
  { key: "map", label: "Map" },
  { key: "stats", label: "Statistics" },
];

function eventsPerMinute(points: { count: number }[] | undefined): string {
  if (!points || points.length === 0) return "—";
  const total = points.reduce((sum, p) => sum + p.count, 0);
  const rate = total / 60; // /stats/timeseries defaults to a 60-minute window
  return rate.toFixed(1);
}

export function TopBar({ view, onChangeView }: { view: View; onChangeView: (v: View) => void }) {
  const { connectionStatus, events } = useThreatFeed();
  const { summary, timeseries } = useStats();

  return (
    <nav className="hud-panel fixed top-4 left-4 right-4 z-20 flex flex-wrap justify-between items-center gap-4 px-4 py-3 pointer-events-auto">
      <ul className="flex gap-4 items-center">
        {TABS.map((tab) => (
          <li key={tab.key}>
            <button
              type="button"
              onClick={() => onChangeView(tab.key)}
              className={`text-[11px] font-bold uppercase tracking-widest pb-1 border-b-2 transition-colors ${
                view === tab.key
                  ? "text-primary-fixed-dim border-primary-fixed-dim"
                  : "text-on-surface-variant border-transparent hover:text-primary-fixed-dim"
              }`}
            >
              {tab.label}
            </button>
          </li>
        ))}
      </ul>

      <dl className="flex gap-6 text-right">
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-on-surface-variant opacity-70">Total Events</dt>
          <dd className="text-sm font-bold text-on-surface">{summary?.total_events ?? events.length}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-on-surface-variant opacity-70">Events / min</dt>
          <dd className="text-sm font-bold text-on-surface">{eventsPerMinute(timeseries?.points)}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-on-surface-variant opacity-70">Feed</dt>
          <dd
            className={`text-sm font-bold uppercase ${
              connectionStatus === "open"
                ? "text-primary-fixed-dim"
                : connectionStatus === "connecting"
                  ? "text-tertiary-fixed-dim"
                  : "text-secondary-container"
            }`}
          >
            {connectionStatus}
          </dd>
        </div>
      </dl>
    </nav>
  );
}
