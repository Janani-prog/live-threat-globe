import { useThreatFeed } from "../context/ThreatFeedContext";
import { parseCategories } from "../lib/categories";
import type { ThreatEvent } from "../lib/types";

function riskTier(score: number | null): { label: string; className: string } {
  if (score === null || score === undefined) {
    return { label: "UNSCORED", className: "text-outline border-outline" };
  }
  if (score >= 66) return { label: "HIGH", className: "text-secondary-container border-secondary-container" };
  if (score >= 33) return { label: "MEDIUM", className: "text-primary-fixed-dim border-primary-fixed-dim" };
  return { label: "LOW", className: "text-tertiary-fixed-dim border-tertiary-fixed-dim" };
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] font-bold uppercase tracking-widest text-on-surface-variant opacity-70 mb-1">
        {label}
      </dt>
      <dd className="text-sm break-all">{value}</dd>
    </div>
  );
}

export function EventDetailPanel() {
  const { selectedEvent, selectEvent } = useThreatFeed();
  if (!selectedEvent) return null;

  const event: ThreatEvent = selectedEvent;
  const categories = parseCategories(event.category);
  const tier = riskTier(event.risk_score);
  const hasScore = event.risk_score !== null && event.risk_score !== undefined;
  const hasConfidence = event.confidence_source !== null && event.confidence_source !== undefined;

  return (
    <aside className="hud-panel fixed right-4 top-4 bottom-4 w-80 z-20 p-4 overflow-y-auto pointer-events-auto text-on-surface">
      <div className="flex justify-between items-center mb-4 border-b border-outline-variant pb-2">
        <h2 className="text-[11px] font-bold uppercase tracking-widest text-primary-fixed-dim">
          Threat Detail
        </h2>
        <button
          type="button"
          onClick={() => selectEvent(null)}
          className="text-on-surface-variant hover:text-primary-fixed-dim transition-colors"
          aria-label="Close threat detail panel"
        >
          &#x2715;
        </button>
      </div>

      <dl className="space-y-4">
        <Row label="IP Hash" value={`${event.ip_hash.slice(0, 16)}…`} />
        <Row label="Country" value={event.country ?? "UNKNOWN"} />
        <Row label="ASN" value={event.asn ?? "UNKNOWN"} />

        <div>
          <dt className="text-[11px] font-bold uppercase tracking-widest text-on-surface-variant opacity-70 mb-1">
            Risk Score
          </dt>
          <dd className={`inline-block border px-2 py-1 text-[11px] font-bold uppercase tracking-widest ${tier.className}`}>
            {tier.label}
            {hasScore ? ` (${event.risk_score!.toFixed(1)})` : ""}
          </dd>
          {!hasScore && (
            <p className="text-xs text-on-surface-variant opacity-60 mt-1">
              Model not yet trained for this event — risk scoring pending.
            </p>
          )}
        </div>

        <Row
          label="AbuseIPDB Confidence"
          value={hasConfidence ? `${event.confidence_source}%` : "UNKNOWN"}
        />

        <div>
          <dt className="text-[11px] font-bold uppercase tracking-widest text-on-surface-variant opacity-70 mb-1">
            Categories
          </dt>
          <dd className="flex flex-wrap gap-1">
            {categories.length > 0 ? (
              categories.map((c) => (
                <span
                  key={c}
                  className="border border-outline-variant px-2 py-0.5 text-[10px] uppercase text-on-surface-variant"
                >
                  {c}
                </span>
              ))
            ) : (
              <span className="text-xs text-on-surface-variant opacity-60">Uncategorized</span>
            )}
          </dd>
        </div>

        <Row
          label="Reported"
          value={event.reported_at ? new Date(event.reported_at).toISOString().replace("T", " ").slice(0, 19) : "UNKNOWN"}
        />
      </dl>
    </aside>
  );
}
