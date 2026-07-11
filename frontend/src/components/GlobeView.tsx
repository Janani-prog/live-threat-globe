import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";
import { DEFAULT_POV, useGlobeControls } from "../context/GlobeControlsContext";
import { useThreatFeed } from "../context/ThreatFeedContext";
import { RISK_COLORS, riskColor } from "../lib/risk";
import type { ThreatEvent } from "../lib/types";

interface GlobePoint extends ThreatEvent {
  lat: number;
  lng: number;
  color: string;
  radius: number;
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
      onGlobeReady={() => {
        registerGlobe(globeRef.current);
        globeRef.current?.pointOfView(DEFAULT_POV, 0);
      }}
    />
  );
}
