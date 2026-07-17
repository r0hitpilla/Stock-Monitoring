import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import History from "./History";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn() } }));
vi.mock("react-chartjs-2", () => ({ Line: () => <div data-testid="price-chart" /> }));

describe("History page", () => {
  it("fetches history and price data once a watch is selected", async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/api/v1/watches") {
        return Promise.resolve({ data: [{ id: 5, product_id: 1, watch_target_id: 7, interval_seconds: 300, is_active: true }] });
      }
      if (url.startsWith("/api/v1/analytics/price-history")) {
        return Promise.resolve({ data: [{ timestamp: "t1", price: 29 }] });
      }
      if (url.startsWith("/api/v1/history")) {
        return Promise.resolve({ data: [{ event_id: 1, event_type: "stock_available", created_at: "t1", snapshot: { availability: "available", price: 29, mrp: 32, discount_pct: 9.4, eta_minutes: 10, store_name: null, image_url: null, quantity_label: null, variants: [], product_url: null } }] });
      }
      return Promise.resolve({ data: [] });
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <History />
      </QueryClientProvider>
    );

    fireEvent.change(await screen.findByRole("combobox"), { target: { value: "5" } });

    await waitFor(() => expect(screen.getByTestId("price-chart")).toBeInTheDocument());
    expect(screen.getByText("stock_available")).toBeInTheDocument();
  });
});
