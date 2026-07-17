import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Logs from "./Logs";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn() } }));

describe("Logs page", () => {
  it("renders recent log entries", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [{ id: 1, level: "error", message: "provider crashed", context: {}, created_at: "t1" }],
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Logs />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByText("provider crashed")).toBeInTheDocument());
  });
});
