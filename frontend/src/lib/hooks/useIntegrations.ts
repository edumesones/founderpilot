/**
 * Integrations hook for managing Gmail/Slack connections.
 */

"use client";

import { create } from "zustand";
import {
  IntegrationsStatusResponse,
  getIntegrationsStatus,
  getGmailConnectUrl,
  getSlackConnectUrl,
  disconnectGmail as apiDisconnectGmail,
  disconnectSlack as apiDisconnectSlack,
} from "../api/integrations";

interface IntegrationsState {
  status: IntegrationsStatusResponse | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchStatus: () => Promise<void>;
  connectGmail: () => Promise<void>;
  connectSlack: () => Promise<void>;
  disconnectGmail: () => Promise<void>;
  disconnectSlack: () => Promise<void>;
  clearError: () => void;
}

export const useIntegrations = create<IntegrationsState>((set, get) => ({
  status: null,
  loading: false,
  error: null,

  fetchStatus: async () => {
    if (get().loading) return;

    set({ loading: true, error: null });

    try {
      const status = await getIntegrationsStatus();
      set({ status, loading: false });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to fetch status",
      });
    }
  },

  connectGmail: async () => {
    set({ loading: true, error: null });

    try {
      const redirectUrl = await getGmailConnectUrl();
      window.location.href = redirectUrl;
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to connect Gmail",
      });
    }
  },

  connectSlack: async () => {
    set({ loading: true, error: null });

    try {
      const redirectUrl = await getSlackConnectUrl();
      window.location.href = redirectUrl;
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to connect Slack",
      });
    }
  },

  disconnectGmail: async () => {
    set({ loading: true, error: null });

    try {
      await apiDisconnectGmail();
      // Refresh status after disconnect
      await get().fetchStatus();
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to disconnect Gmail",
      });
    }
  },

  disconnectSlack: async () => {
    set({ loading: true, error: null });

    try {
      await apiDisconnectSlack();
      // Refresh status after disconnect
      await get().fetchStatus();
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "Failed to disconnect Slack",
      });
    }
  },

  clearError: () => set({ error: null }),
}));

export default useIntegrations;
