import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";
import { DEFAULT_POV, useGlobeControls } from "../context/GlobeControlsContext";
import { useThreatFeed } from "../context/ThreatFeedContext";
import { RISK_COLORS, riskColor, riskTier } from "../lib/risk";
import type { ThreatEvent } from "../lib/types";

interface GlobePoint extends ThreatEvent {
  lat: number;
  lng: number;
  color: string;
  radius: number;
}

interface RingDatum {
  id: number;
  lat: number;
  lng: number;
  color: (t: number) => string;
}

interface ArcDatum {
  id: number;
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  color: string;
}

const RING_LIFETIME_MS = 4000;
const RECENT_ARCS_COUNT = 20;

// A neutral, stylized aggregation point for the attack-vector arcs below —
// not a claimed real victim/target location (we only ever know the
// reporting/attacker IP's geolocation, never a real destination). This is
// the same visual convention the vendor maps referenced in the PRD use:
// arcs converge on a fixed point to read as "reported to this monitoring
// pipeline," not literal traffic-destination geodata.
const MONITORING_HUB = { lat: 20, lng: 0 };

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function fadeColor(hex: string): (t: number) => string {
  const [r, g, b] = hexToRgb(hex);
  return (t: number) => `rgba(${r},${g},${b},${Math.max(1 - t, 0)})`;
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
  const { registerGlobe, autoRotate } = useGlobeControls();
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  const [rings, setRings] = useState<RingDatum[]>([]);
  const seenIds = useRef<Set<number>>(new Set());
  const isFirstEventsUpdate = useRef(true);
  const mountedRef = useRef(true);

  useEffect(() => {
    function onResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    const controls = globe.controls();
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.4;
  }, [autoRotate]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Pulse a ring at newly-arrived high-risk events. Skips the initial REST
  // hydration batch (that's history, not something "arriving" live) and
  // only fires for genuinely new event IDs pushed after that.
  useEffect(() => {
    if (isFirstEventsUpdate.current) {
      events.forEach((e) => seenIds.current.add(e.id));
      isFirstEventsUpdate.current = false;
      return;
    }

    const newHighRisk = events.filter(
      (e) => !seenIds.current.has(e.id) && e.lat !== null && e.lon !== null && riskTier(e.risk_score) === "high",
    );
    events.forEach((e) => seenIds.current.add(e.id));
    if (newHighRisk.length === 0) return;

    const newRings: RingDatum[] = newHighRisk.map((e) => ({
      id: e.id,
      lat: e.lat as number,
      lng: e.lon as number,
      color: fadeColor(RISK_COLORS.high),
    }));
    setRings((prev) => [...prev, ...newRings]);

    setTimeout(() => {
      if (!mountedRef.current) return;
      setRings((prev) => prev.filter((r) => !newRings.some((nr) => nr.id === r.id)));
    }, RING_LIFETIME_MS);
  }, [events]);

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
          color: riskColor(e.risk_score),
          radius: radiusForEvent(e),
        })),
    [events],
  );

  const arcs: ArcDatum[] = useMemo(
    () =>
      events
        .filter((e): e is ThreatEvent & { lat: number; lon: number } => e.lat !== null && e.lon !== null)
        .slice(0, RECENT_ARCS_COUNT)
        .map((e) => ({
          id: e.id,
          startLat: e.lat,
          startLng: e.lon,
          endLat: MONITORING_HUB.lat,
          endLng: MONITORING_HUB.lng,
          color: riskColor(e.risk_score),
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
      atmosphereColor={RISK_COLORS.medium}
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
      ringsData={rings}
      ringLat="lat"
      ringLng="lng"
      ringColor="color"
      ringMaxRadius={6}
      ringPropagationSpeed={3}
      ringRepeatPeriod={RING_LIFETIME_MS / 3}
      arcsData={arcs}
      arcStartLat="startLat"
      arcStartLng="startLng"
      arcEndLat="endLat"
      arcEndLng="endLng"
      arcColor="color"
      arcAltitude={0.3}
      arcStroke={0.4}
      arcDashLength={0.4}
      arcDashGap={0.3}
      arcDashAnimateTime={2500}
      onGlobeReady={() => {
        registerGlobe(globeRef.current);
        globeRef.current?.pointOfView(DEFAULT_POV, 0);
      }}
    />
  );
}
