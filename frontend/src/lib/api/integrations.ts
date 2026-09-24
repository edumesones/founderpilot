/**
 * Integrations API methods.
 */

import apiClient from "./client";

export interface IntegrationStatus {
  provider: string;
  connected: boolean;
  email: string | null;
  workspace_name: string | null;
  connected_at: string | null;
  expires_at: string | null;
}

export interface IntegrationsStatusResponse {
  gmail: IntegrationStatus;
  slack: IntegrationStatus;
  all_connected: boolean;
}

export interface ConnectResponse {
  redirect_url: string;
}

export interface DisconnectResponse {
  message: string;
  provider: string;
}

/**
 * Get status of all integrations.
 */
export async function getIntegrationsStatus(): Promise<IntegrationsStatusResponse> {
  const response = await apiClient.get<IntegrationsStatusResponse>(
    "/api/v1/integrations/status"
  );
  return response.data;
}

/**
 * Get Gmail OAuth URL.
 */
export async function getGmailConnectUrl(): Promise<string> {
  const response = await apiClient.get<ConnectResponse>(
    "/api/v1/integrations/gmail/connect"
  );
  return response.data.redirect_url;
}

/**
 * Disconnect Gmail integration.
 */
export async function disconnectGmail(): Promise<DisconnectResponse> {
  const response = await apiClient.delete<DisconnectResponse>(
    "/api/v1/integrations/gmail"
  );
  return response.data;
}

/**
 * Get Slack OAuth URL.
 */
export async function getSlackConnectUrl(): Promise<string> {
  const response = await apiClient.get<ConnectResponse>(
    "/api/v1/integrations/slack/connect"
  );
  return response.data.redirect_url;
}

/**
 * Disconnect Slack integration.
 */
export async function disconnectSlack(): Promise<DisconnectResponse> {
  const response = await apiClient.delete<DisconnectResponse>(
    "/api/v1/integrations/slack"
  );
  return response.data;
}
