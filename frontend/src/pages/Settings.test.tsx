import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Settings from "./Settings";

vi.mock("../api/client", () => ({ apiClient: { get: vi.fn(), put: vi.fn() } }));

describe("Settings page", () => {
  it("submits an updated setting", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { timezone: "Asia/Kolkata" } });
    vi.mocked(apiClient.put).mockResolvedValue({ data: { timezone: "UTC" } });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Settings />
      </QueryClientProvider>
    );

    fireEvent.change(await screen.findByPlaceholderText("Key"), { target: { value: "timezone" } });
    fireEvent.change(screen.getByPlaceholderText("Value"), { target: { value: "UTC" } });
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() =>
      expect(apiClient.put).toHaveBeenCalledWith("/api/v1/settings", { key: "timezone", value: "UTC" })
    );
  });
});
