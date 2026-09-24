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
import { AnimatedCard, AnimatedButton, LoadingSkeleton } from "@/components/animated";
import { PageTransition } from "@/components/layout";
import { motion } from "framer-motion";

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
    <PageTransition>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        {/* Header with glass effect */}
        <div className="bg-[var(--glass-bg-solid)] backdrop-blur-[var(--glass-blur)] border-b border-[var(--glass-border)] shadow-[var(--shadow-glass)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
              >
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Audit Dashboard
                </h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Complete transparency into all AI agent actions
                </p>
              </motion.div>
              <AnimatedButton
                variant="outline"
                onClick={handleExport}
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
              </AnimatedButton>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <AnimatedCard variant="glass" className="p-4" hover={false}>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Agent Filter */}
            <div>
              <label
                htmlFor="agent-filter"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Agent
              </label>
              <select
                id="agent-filter"
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value)}
                className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
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
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Status
              </label>
              <select
                id="status-filter"
                value={escalatedFilter}
                onChange={(e) => setEscalatedFilter(e.target.value)}
                className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
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
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
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
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Search
              </label>
              <input
                id="search"
                type="text"
                placeholder="Search input/output..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              />
              </div>
            </div>
          </AnimatedCard>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
          <AnimatedCard variant="glass" className="overflow-hidden" hover={false}>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 dark:border-red-500 p-4 m-4"
              >
                <div className="flex">
                  <div className="ml-3">
                    <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
                  </div>
                </div>
              </motion.div>
            )}

            {loading && entries.length === 0 ? (
              <div className="p-6 space-y-4">
                <LoadingSkeleton variant="rect" height={60} count={5} />
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
          </AnimatedCard>
        </div>

        {/* Detail Modal */}
        <AuditDetailModal
          entryId={selectedEntryId}
          onClose={() => setSelectedEntryId(null)}
        />
      </div>
    </PageTransition>
  );
}
