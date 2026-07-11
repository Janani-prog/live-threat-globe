import { ConnectionBadge } from "./components/ConnectionBadge";
import { EventDetailPanel } from "./components/EventDetailPanel";
import { GlobeView } from "./components/GlobeView";
import { ThreatFeedProvider } from "./context/ThreatFeedContext";

function App() {
  return (
    <ThreatFeedProvider>
      <div className="relative h-screen w-screen bg-black overflow-hidden">
        <GlobeView />
        <ConnectionBadge />
        <EventDetailPanel />
      </div>
    </ThreatFeedProvider>
  );
}

export default App;
