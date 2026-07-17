import { useEffect } from "react";
import { useAuthStore } from "../store/authStore";
import { LiveEvent, useLiveEventsStore } from "../store/liveEventsStore";

const RECONNECT_DELAY_MS = 3000;

export function useLiveEvents(): void {
  const accessToken = useAuthStore((s) => s.accessToken);
  const addEvent = useLiveEventsStore((s) => s.addEvent);

  useEffect(() => {
    if (!accessToken) return;

    let socket: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    function connect() {
      const wsUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";
      socket = new WebSocket(`${wsUrl}/ws?token=${accessToken}`);

      socket.onmessage = (event) => {
        const payload: LiveEvent = JSON.parse(event.data);
        addEvent(payload);
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          new Notification(`Update: ${payload.event_type}`);
        }
      };

      socket.onclose = () => {
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [accessToken, addEvent]);
}
