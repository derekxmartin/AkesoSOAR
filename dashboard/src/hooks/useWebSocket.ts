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
 * Hook that connects to the AkesoSOAR WebSocket with exponential backoff.
 * Only connects when a valid access_token is present.
 */
export default function useWebSocket(options: UseWebSocketOptions = {}) {
  const { rooms = ["global"], onMessage } = options;
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const backoffRef = useRef(1000); // start at 1s, max 30s
  const unmountedRef = useRef(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    // Close any existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const roomsParam = rooms.join(",");
    const url = `${proto}//${window.location.host}/ws?token=${token}&rooms=${encodeURIComponent(roomsParam)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      backoffRef.current = 1000; // reset backoff on success
    };

    ws.onclose = () => {
      setConnected(false);
      if (!unmountedRef.current) {
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s max
        const delay = backoffRef.current;
        backoffRef.current = Math.min(delay * 2, 30000);
        reconnectTimer.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror, which handles reconnect
    };

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        if (msg.type === "pong") return; // heartbeat response
        onMessageRef.current?.(msg);
      } catch {
        // ignore non-JSON
      }
    };
  }, [rooms]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  const subscribe = useCallback((room: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ subscribe: room }));
    }
  }, []);

  return { connected, subscribe };
}
