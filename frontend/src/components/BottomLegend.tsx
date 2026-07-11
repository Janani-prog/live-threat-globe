import { RISK_COLORS } from "../lib/risk";

// Adapts the Stitch mockup's bottom nav pattern (row of tabs, each with a
// thin color-coded underline bar) into an actual legend for the globe's
// risk-tier marker colors, rather than the mockup's unrelated placeholder
// product tabs.
const LEGEND_ITEMS: { label: string; color: string }[] = [
  { label: "High Risk", color: RISK_COLORS.high },
  { label: "Medium Risk", color: RISK_COLORS.medium },
  { label: "Low Risk", color: RISK_COLORS.low },
  { label: "Unscored", color: RISK_COLORS.unscored },
];

export function BottomLegend() {
  return (
    <nav className="hud-panel fixed bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-4 px-4 py-2 pointer-events-auto">
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex flex-col items-center gap-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
            {item.label}
          </span>
          <span
            className="block h-[2px] w-10"
            style={{ backgroundColor: item.color }}
            aria-hidden="true"
          />
        </div>
      ))}
    </nav>
  );
}
