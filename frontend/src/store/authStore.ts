import { create } from "zustand";
import { persist } from "zustand/middleware";

interface Tokens {
  accessToken: string;
  refreshToken: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  phoneNumber: string | null;
  login: (tokens: Tokens, phoneNumber: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      phoneNumber: null,
      login: (tokens, phoneNumber) =>
        set({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken, phoneNumber }),
      logout: () => set({ accessToken: null, refreshToken: null, phoneNumber: null }),
    }),
    { name: "auth" }
  )
);
