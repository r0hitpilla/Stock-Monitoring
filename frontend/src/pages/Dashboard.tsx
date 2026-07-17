import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { useLiveEvents } from "../hooks/useLiveEvents";
import { useLiveEventsStore } from "../store/liveEventsStore";

export default function Dashboard() {
  useLiveEvents();
  const events = useLiveEventsStore((s) => s.events);
  const { data: watches } = useQuery({
    queryKey: ["watches"],
    queryFn: async () => (await apiClient.get("/api/v1/watches")).data,
  });

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <div className="rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur">
        Active watches: {watches?.length ?? "…"}
      </div>
      <div className="space-y-2">
        <h2 className="text-lg font-medium">Live feed</h2>
        {events.map((event) => (
          <div key={event.event_id} className="rounded border border-white/10 p-2 text-sm">
            {event.event_type} — watch target {event.watch_target_id}
          </div>
        ))}
      </div>
    </div>
  );
}
