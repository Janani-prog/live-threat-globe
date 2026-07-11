import { useGlobeControls } from "../context/GlobeControlsContext";

// Structure/styling adapted from the Stitch "Cybersecurity Terminal
// Dashboard" mockup's right-side toolbar (fixed vertical icon rail,
// backdrop-blur glass, sharp corners). All four buttons are wired to real
// globe behavior rather than left as decorative placeholders — the
// mockup's "3D toggle" icon is repurposed as an auto-rotate toggle since
// this globe is inherently 3D.
function ToolbarButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={`w-10 h-10 flex items-center justify-center border border-transparent transition-all duration-75 ${
        active
          ? "text-primary-fixed-dim border-primary-fixed-dim bg-surface-container-high"
          : "text-outline-variant hover:bg-surface-container-high hover:text-primary-fixed-dim"
      }`}
    >
      {children}
    </button>
  );
}

export function RightToolbar() {
  const { zoomIn, zoomOut, recenter, toggleAutoRotate, autoRotate } = useGlobeControls();

  return (
    <aside className="hud-panel fixed right-4 top-1/2 -translate-y-1/2 flex flex-col gap-1 p-1 w-12 items-center z-20 pointer-events-auto">
      <ToolbarButton label="Zoom in" onClick={zoomIn}>
        <span className="text-lg leading-none">+</span>
      </ToolbarButton>
      <ToolbarButton label="Zoom out" onClick={zoomOut}>
        <span className="text-lg leading-none">&minus;</span>
      </ToolbarButton>
      <ToolbarButton label="Recenter" onClick={recenter}>
        <span className="text-xs leading-none">&#x2316;</span>
      </ToolbarButton>
      <ToolbarButton label="Toggle auto-rotate" active={autoRotate} onClick={toggleAutoRotate}>
        <span className="text-xs leading-none">&#x21bb;</span>
      </ToolbarButton>
    </aside>
  );
}
