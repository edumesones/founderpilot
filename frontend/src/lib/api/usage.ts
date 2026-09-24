/**
 * API client for usage tracking endpoints.
 */

import { apiClient } from "./client";

export interface AgentUsage {
  count: number;
  limit: number;
  percentage: number;
  overage: number;
  overage_cost_cents: number;
}

export interface UsageAlert {
  agent: string;
  message: string;
  level: "warning" | "error";
}

export interface PlanInfo {
  name: string;
  limits: {
    emails_per_month: number;
    invoices_per_month: number;
    meetings_per_month: number;
  };
}

export interface UsageStatsResponse {
  tenant_id: string;
  period_start: string;
  period_end: string;
  plan: PlanInfo;
  usage: {
    inbox: AgentUsage;
    invoice: AgentUsage;
    meeting: AgentUsage;
  };
  total_overage_cost_cents: number;
  alerts: UsageAlert[];
}

/**
 * Fetch current usage statistics for the authenticated user.
 */
export async function getUsageStats(): Promise<UsageStatsResponse> {
  const response = await apiClient.get<UsageStatsResponse>("/api/v1/usage");
  return response.data;
}
