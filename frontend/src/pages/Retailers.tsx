import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface Retailer {
  slug: string;
  name: string;
  is_active: boolean;
}

export default function Retailers() {
  const { data: retailers = [] } = useQuery<Retailer[]>({
    queryKey: ["retailers"],
    queryFn: async () => (await apiClient.get("/api/v1/retailers")).data,
  });

  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-semibold">Retailers</h1>
      <div className="grid grid-cols-2 gap-4">
        {retailers.map((retailer) => (
          <div key={retailer.slug} className="rounded-lg border border-white/10 p-4 flex items-center justify-between">
            <span>{retailer.name}</span>
            <span className={retailer.is_active ? "text-emerald-400" : "text-red-400"}>
              {retailer.is_active ? "active" : "inactive"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
