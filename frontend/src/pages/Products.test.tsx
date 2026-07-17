import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import Products from "./Products";

vi.mock("../api/client", () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
}));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Products page", () => {
  afterEach(() => vi.resetAllMocks());

  it("renders products returned by the API", async () => {
    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/api/v1/products") {
        return Promise.resolve({ data: [{ id: 1, name: "Milk", keyword: "amul milk 500ml", canonical_image_url: null }] });
      }
      return Promise.resolve({ data: [] });
    });

    renderWithClient(<Products />);

    await waitFor(() => expect(screen.getByText("Milk")).toBeInTheDocument());
  });

  it("submits a new product via the create form", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 1, name: "Bread", keyword: "brown bread", canonical_image_url: null } });

    renderWithClient(<Products />);

    fireEvent.change(await screen.findByPlaceholderText("Name"), { target: { value: "Bread" } });
    fireEvent.change(screen.getByPlaceholderText("Search keyword"), { target: { value: "brown bread" } });
    fireEvent.click(screen.getByText("Add product"));

    await waitFor(() =>
      expect(apiClient.post).toHaveBeenCalledWith("/api/v1/products", {
        name: "Bread",
        keyword: "brown bread",
        canonical_image_url: null,
      })
    );
  });
});
