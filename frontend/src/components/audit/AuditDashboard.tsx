/**
 * Main audit dashboard component with filters and table.
 */

"use client";

import { useState, useEffect } from "react";
import { AuditTable } from "./AuditTable";
import { AuditDetailModal } from "./AuditDetailModal";
import {
  AuditEntry,
  AuditFilters,
  getAuditEntries,
  exportAuditEntries,
} from "@/lib/api/audit";

export function AuditDashboard() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  // Filters
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [escalatedFilter, setEscalatedFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [minConfidence, setMinConfidence] = useState<number>(0);

  // Load entries
  const loadEntries = async (cursor?: string, append = false) => {
    setLoading(true);
    setError(null);

    try {
      const filters: AuditFilters = {
        cursor,
        limit: 50,
      };

      if (agentFilter !== "all") {
        filters.agent = agentFilter as AuditFilters["agent"];
      }
      if (escalatedFilter === "escalated") {
        filters.escalated = true;
      } else if (escalatedFilter === "auto") {
        filters.escalated = false;
      }
      if (searchQuery) {
        filters.search = searchQuery;
      }
      if (minConfidence > 0) {
        filters.min_confidence = minConfidence;
      }

      const response = await getAuditEntries(filters);

      if (append) {
        setEntries((prev) => [...prev, ...response.entries]);
      } else {
        setEntries(response.entries);
      }

      setNextCursor(response.next_cursor);
      setHasMore(response.has_more);
    } catch (err) {
      setError("Failed to load audit entries. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentFilter, escalatedFilter, searchQuery, minConfidence]);

  // Handle load more
  const handleLoadMore = () => {
    if (nextCursor && !loading) {
      loadEntries(nextCursor, true);
    }
  };

  // Handle export
  const handleExport = async () => {
    try {
      const filters: Omit<AuditFilters, "cursor" | "limit"> = {};

      if (agentFilter !== "all") {
        filters.agent = agentFilter as AuditFilters["agent"];
      }
      if (escalatedFilter === "escalated") {
        filters.escalated = true;
      } else if (escalatedFilter === "auto") {
        filters.escalated = false;
      }
      if (searchQuery) {
        filters.search = searchQuery;
      }
      if (minConfidence > 0) {
        filters.min_confidence = minConfidence;
      }

      const blob = await exportAuditEntries(filters);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Failed to export:", err);
      alert("Failed to export audit log. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Audit Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Complete transparency into all AI agent actions
              </p>
            </div>
            <button
              onClick={handleExport}
              className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Agent Filter */}
            <div>
              <label
                htmlFor="agent-filter"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Agent
              </label>
              <select
                id="agent-filter"
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="all">All Agents</option>
                <option value="inbox_pilot">InboxPilot</option>
                <option value="invoice_pilot">InvoicePilot</option>
                <option value="meeting_pilot">MeetingPilot</option>
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <label
                htmlFor="status-filter"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Status
              </label>
              <select
                id="status-filter"
                value={escalatedFilter}
                onChange={(e) => setEscalatedFilter(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="all">All Status</option>
                <option value="auto">Auto</option>
                <option value="escalated">Escalated</option>
              </select>
            </div>

            {/* Confidence Filter */}
            <div>
              <label
                htmlFor="confidence-filter"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Min Confidence ({Math.round(minConfidence * 100)}%)
              </label>
              <input
                id="confidence-filter"
                type="range"
                min="0"
                max="100"
                value={minConfidence * 100}
                onChange={(e) =>
                  setMinConfidence(parseInt(e.target.value) / 100)
                }
                className="block w-full"
              />
            </div>

            {/* Search */}
            <div>
              <label
                htmlFor="search"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Search
              </label>
              <input
                id="search"
                type="text"
                placeholder="Search input/output..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {error && (
            <div className="bg-red-50 border-l-4 border-red-400 p-4 m-4">
              <div className="flex">
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {loading && entries.length === 0 ? (
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : (
            <AuditTable
              entries={entries}
              onSelectEntry={(entry) => setSelectedEntryId(entry.id)}
              onLoadMore={handleLoadMore}
              hasMore={hasMore}
              loading={loading}
            />
          )}
        </div>
      </div>

      {/* Detail Modal */}
      <AuditDetailModal
        entryId={selectedEntryId}
        onClose={() => setSelectedEntryId(null)}
      />
    </div>
  );
}
