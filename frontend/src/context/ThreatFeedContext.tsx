import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { ThreatEvent } from "../lib/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/events";

const MAX_EVENTS = 500;
const BASE_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

type ConnectionStatus = "connecting" | "open" | "closed";

interface ThreatFeedValue {
  events: ThreatEvent[];
  connectionStatus: ConnectionStatus;
  selectedEvent: ThreatEvent | null;
  selectEvent: (event: ThreatEvent | null) => void;
}

const ThreatFeedContext = createContext<ThreatFeedValue | null>(null);

export function ThreatFeedProvider({ children }: { children: ReactNode }) {
  const [events, setEvents] = useState<ThreatEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const [selectedEvent, setSelectedEvent] = useState<ThreatEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const addEvent = useCallback((event: ThreatEvent) => {
    setEvents((prev) => {
      const deduped = prev.filter((e) => e.ip_hash !== event.ip_hash);
      return [event, ...deduped].slice(0, MAX_EVENTS);
    });
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    // Initial hydration from REST so the globe isn't empty on first paint —
    // the backlog-drain cadence (~30s) means the first WS push can take a
    // while, especially right after a cold start.
    fetch(`${API_BASE_URL}/events/recent?limit=200`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data: ThreatEvent[]) => {
        if (mountedRef.current && Array.isArray(data)) setEvents(data);
      })
      .catch(() => {
        // Non-fatal — the WebSocket will still populate the feed live.
      });

    function connect() {
      if (!mountedRef.current) return;
      setConnectionStatus("connecting");

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt.current = 0;
        setConnectionStatus("open");
      };

      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data) as ThreatEvent;
          addEvent(event);
        } catch {
          // Malformed frame — drop it rather than crash the feed.
        }
      };

      ws.onclose = () => {
        setConnectionStatus("closed");
        if (!mountedRef.current) return;
        const attempt = reconnectAttempt.current + 1;
        reconnectAttempt.current = attempt;
        const delay = Math.min(BASE_RECONNECT_DELAY_MS * 2 ** attempt, MAX_RECONNECT_DELAY_MS);
        reconnectTimer.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [addEvent]);

  return (
    <ThreatFeedContext.Provider
      value={{ events, connectionStatus, selectedEvent, selectEvent: setSelectedEvent }}
    >
      {children}
    </ThreatFeedContext.Provider>
  );
}

export function useThreatFeed(): ThreatFeedValue {
  const ctx = useContext(ThreatFeedContext);
  if (!ctx) throw new Error("useThreatFeed must be used within a ThreatFeedProvider");
  return ctx;
}
