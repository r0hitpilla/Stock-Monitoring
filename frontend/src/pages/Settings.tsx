import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { apiClient } from "../api/client";

export default function Settings() {
  const queryClient = useQueryClient();
  const { data: settings = {} } = useQuery<Record<string, unknown>>({
    queryKey: ["settings"],
    queryFn: async () => (await apiClient.get("/api/v1/settings")).data,
  });
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");

  async function save(event: FormEvent) {
    event.preventDefault();
    await apiClient.put("/api/v1/settings", { key, value });
    queryClient.invalidateQueries({ queryKey: ["settings"] });
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <ul className="text-sm space-y-1">
        {Object.entries(settings).map(([k, v]) => (
          <li key={k}>{k}: {String(v)}</li>
        ))}
      </ul>
      <form onSubmit={save} className="flex gap-2">
        <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="Key" className="rounded border px-2 py-1" />
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Value" className="rounded border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Save</button>
      </form>
    </div>
  );
}
