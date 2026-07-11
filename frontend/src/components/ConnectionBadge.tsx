import { useThreatFeed } from "../context/ThreatFeedContext";

const STATUS_STYLES: Record<string, string> = {
  open: "text-primary-fixed-dim border-primary-fixed-dim",
  connecting: "text-tertiary-fixed-dim border-tertiary-fixed-dim",
  closed: "text-secondary-container border-secondary-container",
};

export function ConnectionBadge() {
  const { connectionStatus, events } = useThreatFeed();
  const style = STATUS_STYLES[connectionStatus] ?? STATUS_STYLES.closed;

  return (
    <div
      className={`hud-panel fixed left-4 top-4 z-20 px-3 py-2 text-[11px] font-bold uppercase tracking-widest pointer-events-none ${style}`}
    >
      Feed: {connectionStatus} &middot; {events.length} events
    </div>
  );
}
