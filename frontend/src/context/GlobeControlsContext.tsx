import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import type { GlobeMethods } from "react-globe.gl";

const DEFAULT_POV = { lat: 20, lng: 0, altitude: 2.2 };
const MIN_ALTITUDE = 0.5;
const MAX_ALTITUDE = 4;
const ZOOM_STEP = 0.3;

interface GlobeControlsValue {
  registerGlobe: (methods: GlobeMethods | undefined) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  recenter: () => void;
  toggleAutoRotate: () => void;
  autoRotate: boolean;
}

const GlobeControlsContext = createContext<GlobeControlsValue | null>(null);

export function GlobeControlsProvider({ children }: { children: ReactNode }) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [autoRotate, setAutoRotate] = useState(true);

  const registerGlobe = useCallback((methods: GlobeMethods | undefined) => {
    globeRef.current = methods;
  }, []);

  const zoomBy = useCallback((delta: number) => {
    const globe = globeRef.current;
    if (!globe) return;
    const current = globe.pointOfView();
    const nextAltitude = Math.min(MAX_ALTITUDE, Math.max(MIN_ALTITUDE, current.altitude + delta));
    globe.pointOfView({ altitude: nextAltitude }, 300);
  }, []);

  const zoomIn = useCallback(() => zoomBy(-ZOOM_STEP), [zoomBy]);
  const zoomOut = useCallback(() => zoomBy(ZOOM_STEP), [zoomBy]);

  const recenter = useCallback(() => {
    globeRef.current?.pointOfView(DEFAULT_POV, 600);
  }, []);

  const toggleAutoRotate = useCallback(() => {
    setAutoRotate((prev) => !prev);
  }, []);

  const value = useMemo(
    () => ({ registerGlobe, zoomIn, zoomOut, recenter, toggleAutoRotate, autoRotate }),
    [registerGlobe, zoomIn, zoomOut, recenter, toggleAutoRotate, autoRotate],
  );

  return <GlobeControlsContext.Provider value={value}>{children}</GlobeControlsContext.Provider>;
}

export function useGlobeControls(): GlobeControlsValue {
  const ctx = useContext(GlobeControlsContext);
  if (!ctx) throw new Error("useGlobeControls must be used within a GlobeControlsProvider");
  return ctx;
}

export { DEFAULT_POV };
