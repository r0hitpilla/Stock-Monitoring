import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Line } from "react-chartjs-2";
import {
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { apiClient } from "../api/client";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

interface Watch {
  id: number;
  product_id: number;
  watch_target_id: number;
  interval_seconds: number;
  is_active: boolean;
}

interface PricePoint {
  timestamp: string;
  price: number | null;
}

interface HistoryEntry {
  event_id: number;
  event_type: string;
  created_at: string;
}

export default function History() {
  const [watchId, setWatchId] = useState<number | null>(null);
  const { data: watches = [] } = useQuery<Watch[]>({
    queryKey: ["watches"],
    queryFn: async () => (await apiClient.get("/api/v1/watches")).data,
  });
  const { data: pricePoints = [] } = useQuery<PricePoint[]>({
    queryKey: ["price-history", watchId],
    queryFn: async () => (await apiClient.get(`/api/v1/analytics/price-history?watch_id=${watchId}`)).data,
    enabled: watchId !== null,
  });
  const { data: entries = [] } = useQuery<HistoryEntry[]>({
    queryKey: ["history", watchId],
    queryFn: async () => (await apiClient.get(`/api/v1/history?watch_id=${watchId}`)).data,
    enabled: watchId !== null,
  });

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">History</h1>
      <select onChange={(e) => setWatchId(Number(e.target.value))} className="rounded border px-2 py-1" defaultValue="">
        <option value="" disabled>Select a watch</option>
        {watches.map((watch) => (
          <option key={watch.id} value={watch.id}>watch #{watch.id}</option>
        ))}
      </select>

      {watchId !== null && (
        <>
          <Line
            data={{
              labels: pricePoints.map((p) => p.timestamp),
              datasets: [{ label: "Price", data: pricePoints.map((p) => p.price ?? 0) }],
            }}
          />
          <table className="w-full text-sm">
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.event_id}>
                  <td>{entry.created_at}</td>
                  <td>{entry.event_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
