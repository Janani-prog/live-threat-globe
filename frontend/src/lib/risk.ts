// Single source of truth for risk-tier thresholds/colors, shared by
// GlobeView, EventDetailPanel, and BottomLegend so they can't drift apart.
export const RISK_COLORS = {
  high: "#fe00fe", // neon magenta
  medium: "#00e1ab", // neon cyan
  low: "#00daf8", // neon blue
  // risk_score is frequently null (Phase 2's model artifact is still
  // pending) — this is a distinct neutral, never one of the risk buckets.
  unscored: "#83958c",
} as const;

export type RiskTier = "high" | "medium" | "low" | "unscored";

export function riskTier(score: number | null | undefined): RiskTier {
  if (score === null || score === undefined) return "unscored";
  if (score >= 66) return "high";
  if (score >= 33) return "medium";
  return "low";
}

export function riskColor(score: number | null | undefined): string {
  return RISK_COLORS[riskTier(score)];
}
