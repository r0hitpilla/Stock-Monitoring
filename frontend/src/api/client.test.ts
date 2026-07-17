import { describe, expect, it, beforeEach } from "vitest";
import { useAuthStore } from "../store/authStore";
import { apiClient } from "./client";

describe("apiClient request interceptor", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, phoneNumber: null });
  });

  it("attaches the bearer token from the auth store when present", async () => {
    useAuthStore.getState().login({ accessToken: "access-123", refreshToken: "r" }, "+91999");

    const config = await apiClient.interceptors.request.handlers[0].fulfilled({ headers: {} });

    expect(config.headers.Authorization).toBe("Bearer access-123");
  });

  it("omits the header when no token is present", async () => {
    const config = await apiClient.interceptors.request.handlers[0].fulfilled({ headers: {} });

    expect(config.headers.Authorization).toBeUndefined();
  });
});
