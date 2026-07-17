import { create } from "zustand";

export interface LiveEvent {
  event_id: number;
  watch_target_id: number;
  event_type: string;
  snapshot_id: number;
  created_at: string;
}

interface LiveEventsState {
  events: LiveEvent[];
  addEvent: (event: LiveEvent) => void;
}

const MAX_EVENTS = 100;

export const useLiveEventsStore = create<LiveEventsState>((set) => ({
  events: [],
  addEvent: (event) =>
    set((state) => ({ events: [event, ...state.events].slice(0, MAX_EVENTS) })),
}));
