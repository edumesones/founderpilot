/**
 * Authentication hook with Zustand state management.
 */

"use client";

import { create } from "zustand";
import { User, getCurrentUser, logout as apiLogout, getGoogleAuthUrl } from "../api/auth";

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  initialized: boolean;

  // Actions
  fetchUser: () => Promise<void>;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  error: null,
  initialized: false,

  fetchUser: async () => {
    if (get().loading) return;

    set({ loading: true, error: null });

    try {
      const user = await getCurrentUser();
      set({ user, loading: false, initialized: true });
    } catch (error) {
      set({
        user: null,
        loading: false,
        initialized: true,
        error: error instanceof Error ? error.message : "Failed to fetch user"
      });
    }
  },

  login: async () => {
    set({ loading: true, error: null });

    try {
      const redirectUrl = await getGoogleAuthUrl();
      // Redirect to Google OAuth
      window.location.href = redirectUrl;
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to start login"
      });
    }
  },

  logout: async () => {
    set({ loading: true, error: null });

    try {
      await apiLogout();
      set({ user: null, loading: false });
      window.location.href = "/auth/login";
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to logout"
      });
    }
  },

  clearError: () => set({ error: null }),
}));

export default useAuth;
