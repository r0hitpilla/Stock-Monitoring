import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "../store/authStore";
import { useLiveEventsStore } from "../store/liveEventsStore";
import { useLiveEvents } from "./useLiveEvents";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {}
}

describe("useLiveEvents", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    // @ts-expect-error test double
    global.WebSocket = FakeWebSocket;
    useAuthStore.setState({ accessToken: "access-123", refreshToken: "r", phoneNumber: "+91" });
    useLiveEventsStore.setState({ events: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("connects with the access token in the query string", () => {
    renderHook(() => useLiveEvents());

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toContain("token=access-123");
  });

  it("adds an incoming message to the live events store", () => {
    renderHook(() => useLiveEvents());
    const socket = FakeWebSocket.instances[0];

    socket.onmessage?.({
      data: JSON.stringify({ event_id: 1, watch_target_id: 1, event_type: "stock_available", snapshot_id: 1, created_at: "t1" }),
    });

    expect(useLiveEventsStore.getState().events).toHaveLength(1);
  });
});
