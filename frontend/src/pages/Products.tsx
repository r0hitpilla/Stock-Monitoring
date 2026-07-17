import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { apiClient } from "../api/client";

const RETAILERS = ["blinkit", "zepto", "instamart", "bigbasket"];

interface Product {
  id: number;
  name: string;
  keyword: string;
  canonical_image_url: string | null;
}

interface Watch {
  id: number;
  product_id: number;
  watch_target_id: number;
  interval_seconds: number;
  is_active: boolean;
}

export default function Products() {
  const queryClient = useQueryClient();
  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ["products"],
    queryFn: async () => (await apiClient.get("/api/v1/products")).data,
  });
  const { data: watches = [] } = useQuery<Watch[]>({
    queryKey: ["watches"],
    queryFn: async () => (await apiClient.get("/api/v1/watches")).data,
  });

  const [name, setName] = useState("");
  const [keyword, setKeyword] = useState("");

  async function createProduct(event: FormEvent) {
    event.preventDefault();
    await apiClient.post("/api/v1/products", { name, keyword, canonical_image_url: null });
    setName("");
    setKeyword("");
    queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  async function deleteProduct(id: number) {
    await apiClient.delete(`/api/v1/products/${id}`);
    queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  async function createWatch(productId: number, form: HTMLFormElement) {
    const data = new FormData(form);
    await apiClient.post("/api/v1/watches", {
      product_id: productId,
      retailer_slug: data.get("retailer_slug"),
      city: data.get("city"),
      pincode: data.get("pincode"),
      interval_seconds: Number(data.get("interval_seconds") ?? 300),
    });
    queryClient.invalidateQueries({ queryKey: ["watches"] });
  }

  async function deleteWatch(id: number) {
    await apiClient.delete(`/api/v1/watches/${id}`);
    queryClient.invalidateQueries({ queryKey: ["watches"] });
  }

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Products</h1>

      <form onSubmit={createProduct} className="flex gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className="rounded border px-2 py-1" />
        <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Search keyword" className="rounded border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">Add product</button>
      </form>

      {products.map((product) => (
        <div key={product.id} className="rounded-lg border border-white/10 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{product.name}</div>
              <div className="text-sm text-white/60">{product.keyword}</div>
            </div>
            <button onClick={() => deleteProduct(product.id)} className="text-red-400">Delete</button>
          </div>

          <ul className="text-sm space-y-1">
            {watches.filter((w) => w.product_id === product.id).map((watch) => (
              <li key={watch.id} className="flex items-center justify-between">
                <span>watch #{watch.id} → target {watch.watch_target_id}</span>
                <button onClick={() => deleteWatch(watch.id)} className="text-red-400">Remove</button>
              </li>
            ))}
          </ul>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              createWatch(product.id, e.currentTarget);
              e.currentTarget.reset();
            }}
            className="flex flex-wrap gap-2"
          >
            <select name="retailer_slug" className="rounded border px-2 py-1">
              {RETAILERS.map((slug) => (
                <option key={slug} value={slug}>{slug}</option>
              ))}
            </select>
            <input name="city" placeholder="City" className="rounded border px-2 py-1" />
            <input name="pincode" placeholder="Pincode" className="rounded border px-2 py-1" />
            <input name="interval_seconds" placeholder="Interval (s)" defaultValue={300} className="rounded border px-2 py-1 w-28" />
            <button type="submit" className="rounded bg-emerald-600 px-3 py-1 text-white">Add watch</button>
          </form>
        </div>
      ))}
    </div>
  );
}
