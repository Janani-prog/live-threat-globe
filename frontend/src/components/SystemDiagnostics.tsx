import { useEffect, useState } from "react";
import { useThreatFeed } from "../context/ThreatFeedContext";
import { WS_URL } from "../lib/apiConfig";
import { fetchPipelineHealth, type PipelineHealth } from "../lib/diagnostics";

const POLL_INTERVAL_MS = 10000;

// "LogisticRegression" -> "Logistic Regression" — cosmetic only, the
// underlying value is still the real sklearn class name from the backend.
function spaceCamelCase(s: string): string {
  return s.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function StatusRow({
  label,
  ok,
  okText,
  badText,
  detail,
}: {
  label: string;
  ok: boolean | null;
  okText: string;
  badText: string;
  detail?: string;
}) {
  const color =
    ok === null ? "text-on-surface-variant border-outline" : ok ? "text-primary-fixed-dim border-primary-fixed-dim" : "text-secondary-container border-secondary-container";
  return (
    <div className="flex items-center justify-between py-2 border-b border-outline-variant last:border-b-0">
      <div>
        <div className="text-[11px] font-bold uppercase tracking-widest text-on-surface-variant">{label}</div>
        {detail && <div className="text-xs text-on-surface-variant opacity-60 mt-0.5">{detail}</div>}
      </div>
      <span className={`border px-2 py-1 text-[11px] font-bold uppercase tracking-widest ${color}`}>
        {ok === null ? "UNKNOWN" : ok ? okText : badText}
      </span>
    </div>
  );
}

export function SystemDiagnostics() {
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState<PipelineHealth | null>(null);
  const { connectionStatus } = useThreatFeed();

  useEffect(() => {
    if (!open) return;
    let cancelled = false;

    async function poll() {
      const h = await fetchPipelineHealth();
      if (!cancelled) setHealth(h);
    }

    poll();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [open]);

  const wsSecure = WS_URL.startsWith("wss://");
  const wsConnected = connectionStatus === "open";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hud-panel fixed right-4 bottom-4 z-20 px-3 py-2 text-[11px] font-bold uppercase tracking-widest text-on-surface-variant hover:text-primary-fixed-dim transition-colors pointer-events-auto"
      >
        System Diagnostics
      </button>

      {open && (
        <div
          className="fixed inset-0 z-30 flex items-center justify-center bg-black/70 pointer-events-auto"
          onClick={() => setOpen(false)}
        >
          <div
            className="hud-panel w-full max-w-md p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4 border-b border-outline-variant pb-2">
              <h2 className="text-[11px] font-bold uppercase tracking-widest text-primary-fixed-dim">
                System Diagnostics
              </h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-on-surface-variant hover:text-primary-fixed-dim transition-colors"
                aria-label="Close diagnostics"
              >
                &#x2715;
              </button>
            </div>

            <StatusRow
              label="WebSocket Stream"
              ok={wsConnected}
              okText={wsSecure ? "SECURE / CONNECTED" : "CONNECTED (UNENCRYPTED)"}
              badText={connectionStatus === "connecting" ? "CONNECTING" : "DISCONNECTED"}
              detail={wsSecure ? "wss:// transport" : "ws:// transport (local dev)"}
            />
            <StatusRow
              label="Ingestion Engine"
              ok={health ? health.ingestion_engine.active : null}
              okText="ACTIVE"
              badText="INACTIVE"
              detail="APScheduler background pipeline"
            />
            <StatusRow
              label="ML Classifier Pipeline"
              ok={health ? health.ml_classifier.loaded : null}
              okText={
                health?.ml_classifier.model_type
                  ? `LOADED (${spaceCamelCase(health.ml_classifier.model_type).toUpperCase()})`
                  : "LOADED"
              }
              badText="NOT LOADED"
              detail="backend/app/ml/model.pkl"
            />

            <p className="text-[10px] text-on-surface-variant opacity-50 mt-4">
              Live status, polled from the backend every {POLL_INTERVAL_MS / 1000}s while this panel is open.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
