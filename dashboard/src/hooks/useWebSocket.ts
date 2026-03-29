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

/** Decode JWT payload without a library */
function decodeJwtPayload(token: string): Record<string, any> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    return JSON.parse(atob(parts[1]));
  } catch {
    return null;
  }
}

/** Check if a JWT is expired (with 30s buffer) */
function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 < Date.now() + 30_000;
}

/**
 * Hook that connects to the AkesoSOAR WebSocket with exponential backoff.
 * Stops reconnecting on auth failure (code 4001) or expired token.
 */
export default function useWebSocket(options: UseWebSocketOptions = {}) {
  const { rooms = ["global"], onMessage } = options;
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const backoffRef = useRef(2000);
  const unmountedRef = useRef(false);
  const authFailedRef = useRef(false);
  const connectingRef = useRef(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (unmountedRef.current || authFailedRef.current || connectingRef.current)
      return;

    const token = localStorage.getItem("access_token");
    if (!token || isTokenExpired(token)) {
      // Don't reconnect — token is missing or expired
      authFailedRef.current = true;
      return;
    }

    // Prevent concurrent connection attempts
    connectingRef.current = true;

    // Close any existing connection cleanly
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const roomsParam = rooms.join(",");
    const url = `${proto}//${window.location.host}/ws?token=${token}&rooms=${encodeURIComponent(roomsParam)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      connectingRef.current = false;
      setConnected(true);
      backoffRef.current = 2000; // reset on success
    };

    ws.onclose = (event) => {
      connectingRef.current = false;
      setConnected(false);
      wsRef.current = null;

      // 4001 = auth failure — don't reconnect
      if (event.code === 4001) {
        authFailedRef.current = true;
        return;
      }

      // If token expired while connected, stop
      const tok = localStorage.getItem("access_token");
      if (!tok || isTokenExpired(tok)) {
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
      connectingRef.current = false;
      // onclose fires after onerror — reconnect logic is there
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
    connectingRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
        wsRef.current = null;
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
