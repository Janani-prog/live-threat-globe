export interface ThreatEvent {
  id: number;
  ip_hash: string;
  lat: number | null;
  lon: number | null;
  country: string | null;
  asn: string | null;
  /** Comma-separated AbuseIPDB category IDs, e.g. "4,14,18" — or null if
   * the /check quota guard was hit before this event could be enriched. */
  category: string | null;
  /** Real discovery provenance — which feed actually returned this IP
   * ("AbuseIPDB", "Blocklist.de", "CINS Army"). Null for events ingested
   * before this field existed. */
  source: string | null;
  /** AbuseIPDB's own confidence score (0-100), independent of risk_score. */
  confidence_source: number | null;
  /** Model-derived 0-100 DDoS-relevance score. Null until the Phase 2
   * training artifact exists, or if this event predates it — always
   * render this as an explicit "pending/unscored" state, never as 0. */
  risk_score: number | null;
  reported_at: string | null;
  ingested_at: string;
}
