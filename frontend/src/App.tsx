import { useState } from "react";
import { BottomLegend } from "./components/BottomLegend";
import { EventDetailPanel } from "./components/EventDetailPanel";
import { GlobeView } from "./components/GlobeView";
import { RightToolbar } from "./components/RightToolbar";
import { StatsDashboard } from "./components/StatsDashboard";
import { SystemDiagnostics } from "./components/SystemDiagnostics";
import { ThreatMatrix } from "./components/ThreatMatrix";
import { TopBar } from "./components/TopBar";
import { GlobeControlsProvider } from "./context/GlobeControlsContext";
import { StatsProvider } from "./context/StatsContext";
import { ThreatFeedProvider } from "./context/ThreatFeedContext";
import type { View } from "./lib/view";

function App() {
  const [view, setView] = useState<View>("map");

  return (
    <ThreatFeedProvider>
      <StatsProvider>
        <GlobeControlsProvider>
          <div className="relative h-screen w-screen bg-black overflow-hidden">
            <GlobeView />
            <TopBar view={view} onChangeView={setView} />
            {view === "map" && (
              <>
                <ThreatMatrix />
                <RightToolbar />
                <EventDetailPanel />
              </>
            )}
            {view === "stats" && <StatsDashboard />}
            <BottomLegend />
            <SystemDiagnostics />
          </div>
        </GlobeControlsProvider>
      </StatsProvider>
    </ThreatFeedProvider>
  );
}

export default App;
