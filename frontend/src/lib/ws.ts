"use client";

import { useEffect, useState, useCallback } from "react";
import { getAccessToken } from "./auth";
import type { WSMessage } from "./types";

type MessageHandler = (data: unknown) => void;

class WSManager {
  private ws: WebSocket | null = null;
  private listeners = new Map<string, Set<MessageHandler>>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private url: string | null = null;
  private failures = 0;
  private maxFailures = 10; // Allow more retries now that WS proxy is via Nginx

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    // ponytail: stop retrying when WS proxy is broken (OLS limitation)
    // upgrade path: switch to Nginx or expose WS on separate port
    if (this.failures >= this.maxFailures) return;

    const token = getAccessToken();
    if (!token) return;

    // Use dedicated WS endpoint if configured, otherwise fallback to same host
    const wsBase = process.env.NEXT_PUBLIC_WS_URL;
    if (wsBase) {
      this.url = `${wsBase}/ws/dashboard?token=${token}`;
    } else {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      this.url = `${protocol}//${window.location.host}/ws/dashboard?token=${token}`;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectDelay = 1000;
        this.failures = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          const handlers = this.listeners.get(msg.type);
          if (handlers) {
            handlers.forEach((fn) => fn(msg.data));
          }
        } catch {
          // ignore malformed messages
        }
      };

      this.ws.onclose = () => {
        this.failures++;
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      this.failures++;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer || this.failures >= this.maxFailures) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  subscribe(type: string, handler: MessageHandler) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(handler);
  }

  unsubscribe(type: string, handler: MessageHandler) {
    this.listeners.get(type)?.delete(handler);
  }

  send(data: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      // Prevent "closed before established" console error on page navigation
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
      this.ws = null;
    }
  }
}

// Singleton
let wsInstance: WSManager | null = null;

export function getWSManager(): WSManager {
  if (!wsInstance) {
    wsInstance = new WSManager();
  }
  return wsInstance;
}

/**
 * React hook that subscribes to a WebSocket message type
 * and returns the latest data received.
 */
export function useWebSocket<T>(type: string): T | null {
  const [data, setData] = useState<T | null>(null);

  const handler = useCallback((payload: unknown) => {
    setData(payload as T);
  }, []);

  useEffect(() => {
    const mgr = getWSManager();
    mgr.subscribe(type, handler);
    return () => {
      mgr.unsubscribe(type, handler);
    };
  }, [type, handler]);

  return data;
}
