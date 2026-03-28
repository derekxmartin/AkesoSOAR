import { useCallback, useEffect, useRef, useState } from "react";

export interface WsMessage {
  type: string;
  timestamp?: string;
  [key: string]: any;
}

interface UseWebSocketOptions {
  rooms?: string[];
  onMessage?: (msg: WsMessage) => void;
}

/**
 * Hook that connects to the AkesoSOAR WebSocket and auto-reconnects.
 * Only connects when a valid access_token is present.
 */
export default function useWebSocket(options: UseWebSocketOptions = {}) {
  const { rooms = ["global"], onMessage } = options;
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const roomsParam = rooms.join(",");
    const url = `${proto}//${window.location.host}/ws?token=${token}&rooms=${encodeURIComponent(roomsParam)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        onMessageRef.current?.(msg);
      } catch {
        // ignore non-JSON
      }
    };
  }, [rooms]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((room: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ subscribe: room }));
    }
  }, []);

  return { connected, subscribe };
}
