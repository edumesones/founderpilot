/**
 * Audit log table component displaying agent actions.
 */

"use client";

import { useState } from "react";
import { AuditEntry } from "@/lib/api/audit";

interface AuditTableProps {
  entries: AuditEntry[];
  onSelectEntry: (entry: AuditEntry) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  loading?: boolean;
}

/**
 * Get confidence level color and label.
 */
function getConfidenceDisplay(confidence: number) {
  if (confidence >= 0.9) {
    return {
      color: "bg-green-500",
      label: "High",
      textColor: "text-green-700",
    };
  } else if (confidence >= 0.7) {
    return {
      color: "bg-yellow-500",
      label: "Medium",
      textColor: "text-yellow-700",
    };
  } else {
    return {
      color: "bg-red-500",
      label: "Low",
      textColor: "text-red-700",
    };
  }
}

/**
 * Format agent type to display name.
 */
function formatAgentType(agentType: string): string {
  const map: Record<string, string> = {
    inbox_pilot: "InboxPilot",
    invoice_pilot: "InvoicePilot",
    meeting_pilot: "MeetingPilot",
  };
  return map[agentType] || agentType;
}

/**
 * Format timestamp to relative time.
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

export function AuditTable({
  entries,
  onSelectEntry,
  onLoadMore,
  hasMore = false,
  loading = false,
}: AuditTableProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="text-gray-400 text-6xl mb-4">📋</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No agent activity yet
        </h3>
        <p className="text-gray-500 text-center max-w-md">
          Your agents will appear here once they start working. Actions from
          InboxPilot, InvoicePilot, and MeetingPilot will be logged here.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Agent
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Decision
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {entries.map((entry) => {
              const confidenceDisplay = getConfidenceDisplay(entry.confidence);
              const isHovered = hoveredId === entry.id;

              return (
                <tr
                  key={entry.id}
                  onClick={() => onSelectEntry(entry)}
                  onMouseEnter={() => setHoveredId(entry.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`
                    cursor-pointer transition-colors
                    ${isHovered ? "bg-gray-50" : ""}
                    hover:bg-gray-50
                  `}
                >
                  {/* Time */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatTimestamp(entry.timestamp)}
                  </td>

                  {/* Agent */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {formatAgentType(entry.agent_type)}
                    </span>
                  </td>

                  {/* Action */}
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {entry.action}
                  </td>

                  {/* Decision */}
                  <td className="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">
                    {entry.decision}
                  </td>

                  {/* Confidence */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2 w-20">
                        <div
                          className={`h-2 rounded-full ${confidenceDisplay.color}`}
                          style={{ width: `${entry.confidence * 100}%` }}
                        />
                      </div>
                      <span
                        className={`text-xs font-medium ${confidenceDisplay.textColor}`}
                      >
                        {Math.round(entry.confidence * 100)}%
                      </span>
                    </div>
                  </td>

                  {/* Status */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    {entry.escalated ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        👤 Escalated
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ⚡ Auto
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Load More Button */}
      {hasMore && (
        <div className="flex justify-center py-6 border-t border-gray-200">
          <button
            onClick={onLoadMore}
            disabled={loading}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-700" />
                Loading...
              </span>
            ) : (
              "Load More"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
