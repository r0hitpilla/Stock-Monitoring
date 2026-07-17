import { describe, expect, it, beforeEach } from "vitest";
import { useAuthStore } from "./authStore";

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, refreshToken: null, phoneNumber: null });
  });

  it("stores tokens and phone number on login", () => {
    useAuthStore.getState().login(
      { accessToken: "access-123", refreshToken: "refresh-456" },
      "+919999999999"
    );

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("access-123");
    expect(state.refreshToken).toBe("refresh-456");
    expect(state.phoneNumber).toBe("+919999999999");
  });

  it("clears state on logout", () => {
    useAuthStore.getState().login({ accessToken: "a", refreshToken: "b" }, "+919999999999");
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
  });
});
