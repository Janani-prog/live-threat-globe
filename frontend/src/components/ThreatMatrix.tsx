import { useEffect, useRef } from "react";
import { useThreatFeed } from "../context/ThreatFeedContext";
import { RISK_COLORS, riskTier } from "../lib/risk";
import type { ThreatEvent } from "../lib/types";

const MAX_MATRIX_ENTRIES = 50;

function formatTime(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return "--:--:--";
  return d.toLocaleTimeString([], { hour12: false });
}

function formatLine(event: ThreatEvent): string {
  const time = formatTime(event.ingested_at);
  // Never the raw IP — the backend never sends one (see
  // 03_SECURITY_AND_ACCESS.md). This is a truncated view of the salted
  // one-way hash, clearly labeled as such.
  const hash = `${event.ip_hash.slice(0, 12)}…`;
  const source = event.source ?? "Unknown";
  const scoreText =
    event.risk_score === null || event.risk_score === undefined
      ? "PENDING"
      : `${event.risk_score.toFixed(0)}% (${riskTier(event.risk_score).toUpperCase()})`;
  return `[${time}] HASH: ${hash} | Source: ${source} | ML Score: ${scoreText} | Action: LOGGED`;
}

export function ThreatMatrix() {
  const { events } = useThreatFeed();
  const scrollRef = useRef<HTMLDivElement>(null);

  // ThreatFeedContext's ring buffer is newest-first; show only the most
  // recent MAX_MATRIX_ENTRIES, re-ordered oldest-to-newest so this reads
  // like a scrolling console log rather than a static newest-on-top list.
  const entries = events.slice(0, MAX_MATRIX_ENTRIES).slice().reverse();

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries.length]);

  return (
    <aside className="hud-panel fixed left-4 top-24 bottom-20 w-[26rem] z-20 flex flex-col pointer-events-auto">
      <div className="px-3 py-2 border-b border-outline-variant flex items-baseline justify-between">
        <h2 className="text-[11px] font-bold uppercase tracking-widest text-primary-fixed-dim">
          Live Threat Matrix
        </h2>
        <span className="text-[10px] text-on-surface-variant opacity-60">
          {entries.length}/{MAX_MATRIX_ENTRIES}
        </span>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-1 font-mono text-[11px] leading-relaxed"
      >
        {entries.length === 0 && (
          <p className="text-on-surface-variant opacity-60">Awaiting live events&hellip;</p>
        )}
        {entries.map((event) => {
          const color = RISK_COLORS[riskTier(event.risk_score)];
          return (
            <div key={event.id} style={{ color }} className="whitespace-pre-wrap break-all">
              {formatLine(event)}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
