import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface SystemLog {
  id: number;
  level: string;
  message: string;
  created_at: string;
}

export default function Logs() {
  const { data: logs = [] } = useQuery<SystemLog[]>({
    queryKey: ["logs"],
    queryFn: async () => (await apiClient.get("/api/v1/logs")).data,
  });

  return (
    <div className="p-8 space-y-2">
      <h1 className="text-2xl font-semibold">Logs</h1>
      {logs.map((log) => (
        <div key={log.id} className="rounded border border-white/10 p-2 text-sm">
          <span className="uppercase text-white/50">{log.level}</span> — {log.message} — {log.created_at}
        </div>
      ))}
    </div>
  );
}
