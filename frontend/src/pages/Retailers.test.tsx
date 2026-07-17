import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Retailers from "./Retailers";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn() } }));

describe("Retailers page", () => {
  it("renders each retailer with its active status", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [
        { slug: "blinkit", name: "Blinkit", is_active: true },
        { slug: "zepto", name: "Zepto", is_active: false },
      ],
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Retailers />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByText("Blinkit")).toBeInTheDocument());
    expect(screen.getByText("Zepto")).toBeInTheDocument();
    expect(screen.getAllByText(/active/i)).toHaveLength(2);
  });
});
