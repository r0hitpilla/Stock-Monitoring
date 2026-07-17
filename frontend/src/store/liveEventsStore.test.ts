import { describe, expect, it, beforeEach } from "vitest";
import { useLiveEventsStore } from "./liveEventsStore";

describe("useLiveEventsStore", () => {
  beforeEach(() => {
    useLiveEventsStore.setState({ events: [] });
  });

  it("prepends new events", () => {
    const store = useLiveEventsStore.getState();
    store.addEvent({ event_id: 1, watch_target_id: 1, event_type: "stock_available", snapshot_id: 1, created_at: "t1" });
    store.addEvent({ event_id: 2, watch_target_id: 1, event_type: "price_changed", snapshot_id: 2, created_at: "t2" });

    expect(useLiveEventsStore.getState().events.map((e) => e.event_id)).toEqual([2, 1]);
  });

  it("caps the feed at 100 events", () => {
    const store = useLiveEventsStore.getState();
    for (let i = 0; i < 105; i++) {
      store.addEvent({ event_id: i, watch_target_id: 1, event_type: "stock_available", snapshot_id: i, created_at: "t" });
    }

    expect(useLiveEventsStore.getState().events).toHaveLength(100);
    expect(useLiveEventsStore.getState().events[0].event_id).toBe(104);
  });
});
