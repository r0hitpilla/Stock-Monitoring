import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Notifications from "./Notifications";

vi.mock("../api/client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

describe("Notifications page", () => {
  it("verifies an unverified channel", async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/api/v1/notifications/channels") {
        return Promise.resolve({ data: [{ id: 1, type: "telegram", config: { chat_id: "123" }, is_verified: false }] });
      }
      return Promise.resolve({ data: [] });
    });
    vi.mocked(apiClient.post).mockResolvedValue({ data: { status: "verified" } });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Notifications />
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByText("Verify"));

    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/notifications/channels/1/verify")
    );
  });
});
