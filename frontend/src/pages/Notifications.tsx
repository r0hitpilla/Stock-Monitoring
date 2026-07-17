import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { apiClient } from "../api/client";

interface Channel {
  id: number;
  type: string;
  config: Record<string, unknown>;
  is_verified: boolean;
}

interface LogEntry {
  id: number;
  detection_event_id: number;
  channel_id: number;
  status: string;
  sent_at: string;
}

export default function Notifications() {
  const queryClient = useQueryClient();
  const { data: channels = [] } = useQuery<Channel[]>({
    queryKey: ["channels"],
    queryFn: async () => (await apiClient.get("/api/v1/notifications/channels")).data,
  });
  const { data: log = [] } = useQuery<LogEntry[]>({
    queryKey: ["notification-log"],
    queryFn: async () => (await apiClient.get("/api/v1/notifications/log")).data,
  });
  const [type, setType] = useState("telegram");
  const [config, setConfig] = useState("{}");

  async function addChannel(event: FormEvent) {
    event.preventDefault();
    await apiClient.post("/api/v1/notifications/channels", { type, config: JSON.parse(config) });
    queryClient.invalidateQueries({ queryKey: ["channels"] });
  }

  async function verify(id: number) {
    await apiClient.post(`/api/v1/notifications/channels/${id}/verify`);
    queryClient.invalidateQueries({ queryKey: ["channels"] });
  }

  async function remove(id: number) {
    await apiClient.delete(`/api/v1/notifications/channels/${id}`);
    queryClient.invalidateQueries({ queryKey: ["channels"] });
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Notifications</h1>

      <form onSubmit={addChannel} className="flex gap-2">
        <select value={type} onChange={(e) => setType(e.target.value)} className="rounded border px-2 py-1">
          <option value="telegram">telegram</option>
          <option value="discord">discord</option>
          <option value="email">email</option>
        </select>
        <input value={config} onChange={(e) => setConfig(e.target.value)} className="rounded border px-2 py-1 flex-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Add channel</button>
      </form>

      <ul className="space-y-2">
        {channels.map((channel) => (
          <li key={channel.id} className="flex items-center justify-between rounded border border-white/10 p-2">
            <span>{channel.type} — {channel.is_verified ? "verified" : "unverified"}</span>
            <div className="flex gap-2">
              {!channel.is_verified && (
                <button onClick={() => verify(channel.id)} className="text-emerald-400">Verify</button>
              )}
              <button onClick={() => remove(channel.id)} className="text-red-400">Delete</button>
            </div>
          </li>
        ))}
      </ul>

      <h2 className="text-lg font-medium">Recent notifications</h2>
      <ul className="text-sm space-y-1">
        {log.map((entry) => (
          <li key={entry.id}>{entry.sent_at} — channel {entry.channel_id} — {entry.status}</li>
        ))}
      </ul>
    </div>
  );
}
