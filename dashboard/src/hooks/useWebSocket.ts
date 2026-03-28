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
 * Stops reconnecting on auth failure (code 4001) or when unmounted.
 */
export default function useWebSocket(options: UseWebSocketOptions = {}) {
  const { rooms = ["global"], onMessage } = options;
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const backoffRef = useRef(2000);
  const unmountedRef = useRef(false);
  const authFailedRef = useRef(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (unmountedRef.current || authFailedRef.current) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    // Close any existing connection cleanly
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
      backoffRef.current = 2000; // reset on success
    };

    ws.onclose = (event) => {
      setConnected(false);
      // 4001 = auth failure — don't reconnect
      if (event.code === 4001) {
        authFailedRef.current = true;
        return;
      }
      if (!unmountedRef.current) {
        const delay = backoffRef.current;
        backoffRef.current = Math.min(delay * 2, 30000);
        reconnectTimer.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      // onclose fires after onerror
    };

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        // Server sends error on auth failure before closing
        if (msg.type === "error" && msg.code === 4001) {
          authFailedRef.current = true;
          return;
        }
        if (msg.type === "pong") return;
        onMessageRef.current?.(msg);
      } catch {
        // ignore non-JSON
      }
    };
  }, [rooms]);

  useEffect(() => {
    unmountedRef.current = false;
    authFailedRef.current = false;
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
