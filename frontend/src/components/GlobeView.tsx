import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";
import { useThreatFeed } from "../context/ThreatFeedContext";
import type { ThreatEvent } from "../lib/types";

// Neon accents from the Stitch "Terminal Protocol" design system.
const NEON_MAGENTA = "#fe00fe"; // high risk
const NEON_CYAN = "#00e1ab"; // medium risk
const NEON_BLUE = "#00daf8"; // low risk
// risk_score is frequently null (Phase 2's model artifact is still
// pending) — render unscored points in a dim neutral outline color rather
// than guessing, crashing, or defaulting into one of the risk buckets.
const UNSCORED_GRAY = "#83958c";

interface GlobePoint extends ThreatEvent {
  lat: number;
  lng: number;
  color: string;
  radius: number;
}

function colorForEvent(event: ThreatEvent): string {
  if (event.risk_score === null || event.risk_score === undefined) return UNSCORED_GRAY;
  if (event.risk_score >= 66) return NEON_MAGENTA;
  if (event.risk_score >= 33) return NEON_CYAN;
  return NEON_BLUE;
}

function radiusForEvent(event: ThreatEvent): number {
  // Fall back to AbuseIPDB's raw confidence when we have no model score yet,
  // so unscored points are still visually differentiated by severity.
  const score = event.risk_score ?? event.confidence_source ?? 20;
  const clamped = Math.min(Math.max(score, 0), 100);
  return 0.25 + (clamped / 100) * 0.85;
}

export function GlobeView() {
  const { events, selectEvent } = useThreatFeed();
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    function onResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Dark, near-black sphere (no earth texture) to match the Stitch mockup's
  // custom three.js globe, rather than react-globe.gl's default photo texture.
  const globeMaterial = useMemo(
    () =>
      new THREE.MeshPhongMaterial({
        color: 0x0a0a0a,
        transparent: true,
        opacity: 0.92,
        shininess: 5,
      }),
    [],
  );

  const points: GlobePoint[] = useMemo(
    () =>
      events
        .filter((e): e is ThreatEvent & { lat: number; lon: number } => e.lat !== null && e.lon !== null)
        .map((e) => ({
          ...e,
          lat: e.lat,
          lng: e.lon,
          color: colorForEvent(e),
          radius: radiusForEvent(e),
        })),
    [events],
  );

  return (
    <Globe
      ref={globeRef}
      width={dimensions.width}
      height={dimensions.height}
      backgroundColor="rgba(0,0,0,0)"
      globeImageUrl={null}
      globeMaterial={globeMaterial}
      showGraticules
      showAtmosphere
      atmosphereColor={NEON_CYAN}
      atmosphereAltitude={0.18}
      pointsData={points}
      pointLat="lat"
      pointLng="lng"
      pointColor="color"
      pointRadius="radius"
      pointAltitude={0.012}
      pointsMerge={false}
      pointLabel={(d) => {
        const p = d as GlobePoint;
        const risk = p.risk_score === null || p.risk_score === undefined ? "PENDING" : p.risk_score.toFixed(0);
        return `${p.country ?? "UNKNOWN"} · RISK ${risk}`;
      }}
      onPointClick={(point) => selectEvent(point as GlobePoint)}
      showPointerCursor
      enablePointerInteraction
    />
  );
}
