/**
 * Modal component for displaying detailed audit entry information.
 */

"use client";

import { useEffect, useState } from "react";
import { AuditEntryDetail, getAuditEntry } from "@/lib/api/audit";

interface AuditDetailModalProps {
  entryId: string | null;
  onClose: () => void;
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
      bgColor: "bg-green-50",
    };
  } else if (confidence >= 0.7) {
    return {
      color: "bg-yellow-500",
      label: "Medium",
      textColor: "text-yellow-700",
      bgColor: "bg-yellow-50",
    };
  } else {
    return {
      color: "bg-red-500",
      label: "Low",
      textColor: "text-red-700",
      bgColor: "bg-red-50",
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

export function AuditDetailModal({ entryId, onClose }: AuditDetailModalProps) {
  const [entry, setEntry] = useState<AuditEntryDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entryId) {
      setEntry(null);
      return;
    }

    const loadEntry = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getAuditEntry(entryId);
        setEntry(data);
      } catch (err) {
        setError("Failed to load audit entry details");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadEntry();
  }, [entryId]);

  if (!entryId) return null;

  const confidenceDisplay = entry
    ? getConfidenceDisplay(entry.confidence)
    : null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden"
      onClick={onClose}
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      {/* Background overlay */}
      <div className="absolute inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />

      {/* Modal panel */}
      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div
          className="w-screen max-w-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex h-full flex-col overflow-y-scroll bg-white shadow-xl">
            {/* Header */}
            <div className="bg-gray-50 px-6 py-6 border-b border-gray-200">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2
                    id="modal-title"
                    className="text-lg font-medium text-gray-900"
                  >
                    Audit Entry Details
                  </h2>
                  {entry && (
                    <p className="mt-1 text-sm text-gray-500">
                      {new Date(entry.timestamp).toLocaleString()}
                    </p>
                  )}
                </div>
                <button
                  onClick={onClose}
                  className="ml-3 rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <span className="sr-only">Close panel</span>
                  <svg
                    className="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="1.5"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 px-6 py-6">
              {loading && (
                <div className="flex justify-center items-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                </div>
              )}

              {error && (
                <div className="rounded-md bg-red-50 p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">
                        Error
                      </h3>
                      <div className="mt-2 text-sm text-red-700">{error}</div>
                    </div>
                  </div>
                </div>
              )}

              {entry && !loading && !error && (
                <div className="space-y-6">
                  {/* Overview */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 mb-3">
                      Overview
                    </h3>
                    <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs font-medium text-gray-500">
                          Agent
                        </dt>
                        <dd className="mt-1">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {formatAgentType(entry.agent_type)}
                          </span>
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium text-gray-500">
                          Action
                        </dt>
                        <dd className="mt-1 text-sm text-gray-900">
                          {entry.action}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium text-gray-500">
                          Status
                        </dt>
                        <dd className="mt-1">
                          {entry.escalated ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              👤 Escalated
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              ⚡ Auto
                            </span>
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-medium text-gray-500">
                          Authorized By
                        </dt>
                        <dd className="mt-1 text-sm text-gray-900">
                          {entry.authorized_by}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  {/* Confidence */}
                  {confidenceDisplay && (
                    <div
                      className={`rounded-lg p-4 ${confidenceDisplay.bgColor}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900">
                          Confidence Level
                        </span>
                        <span
                          className={`text-sm font-medium ${confidenceDisplay.textColor}`}
                        >
                          {Math.round(entry.confidence * 100)}% -{" "}
                          {confidenceDisplay.label}
                        </span>
                      </div>
                      <div className="w-full bg-white rounded-full h-3">
                        <div
                          className={`h-3 rounded-full ${confidenceDisplay.color}`}
                          style={{ width: `${entry.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Decision */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 mb-2">
                      Decision
                    </h3>
                    <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">
                      {entry.decision}
                    </p>
                  </div>

                  {/* Input */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 mb-2">
                      Input
                    </h3>
                    <div className="bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
                      <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                        {entry.input_full}
                      </pre>
                    </div>
                  </div>

                  {/* Output */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 mb-2">
                      Output
                    </h3>
                    <div className="bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
                      <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                        {entry.output_full}
                      </pre>
                    </div>
                  </div>

                  {/* Metadata */}
                  {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 mb-2">
                        Metadata
                      </h3>
                      <div className="bg-gray-50 rounded-lg p-3 max-h-48 overflow-y-auto">
                        <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                          {JSON.stringify(entry.metadata, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Trace Link */}
                  {entry.trace_id && (
                    <div>
                      <a
                        href={`https://cloud.langfuse.com/trace/${entry.trace_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800"
                      >
                        View in Langfuse
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
                            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                          />
                        </svg>
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
