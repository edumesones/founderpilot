/**
 * Audit API methods for agent action audit logs.
 */

import apiClient from "./client";

export interface AuditEntry {
  id: string;
  timestamp: string;
  agent_type: "inbox_pilot" | "invoice_pilot" | "meeting_pilot";
  action: string;
  input_summary: string;
  output_summary: string;
  decision: string;
  confidence: number;
  escalated: boolean;
  authorized_by: string;
  trace_id: string | null;
}

export interface AuditEntryDetail extends AuditEntry {
  input_full: string;
  output_full: string;
  metadata: Record<string, unknown>;
}

export interface AuditListResponse {
  entries: AuditEntry[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface AuditFilters {
  agent?: "inbox_pilot" | "invoice_pilot" | "meeting_pilot";
  from?: string; // ISO 8601 date
  to?: string; // ISO 8601 date
  min_confidence?: number; // 0-1
  escalated?: boolean;
  search?: string;
  cursor?: string;
  limit?: number;
}

/**
 * Get paginated list of audit entries with optional filters.
 */
export async function getAuditEntries(
  filters?: AuditFilters
): Promise<AuditListResponse> {
  const params = new URLSearchParams();

  if (filters?.agent) params.append("agent", filters.agent);
  if (filters?.from) params.append("from", filters.from);
  if (filters?.to) params.append("to", filters.to);
  if (filters?.min_confidence !== undefined) {
    params.append("min_confidence", filters.min_confidence.toString());
  }
  if (filters?.escalated !== undefined) {
    params.append("escalated", filters.escalated.toString());
  }
  if (filters?.search) params.append("search", filters.search);
  if (filters?.cursor) params.append("cursor", filters.cursor);
  if (filters?.limit) params.append("limit", filters.limit.toString());

  const response = await apiClient.get<AuditListResponse>(
    `/api/v1/audit?${params.toString()}`
  );
  return response.data;
}

/**
 * Get detailed audit entry by ID.
 */
export async function getAuditEntry(id: string): Promise<AuditEntryDetail> {
  const response = await apiClient.get<AuditEntryDetail>(`/api/v1/audit/${id}`);
  return response.data;
}

/**
 * Export audit entries to CSV.
 */
export async function exportAuditEntries(
  filters?: Omit<AuditFilters, "cursor" | "limit">
): Promise<Blob> {
  const response = await apiClient.post(
    "/api/v1/audit/export",
    { filters, format: "csv" },
    { responseType: "blob" }
  );
  return response.data;
}
