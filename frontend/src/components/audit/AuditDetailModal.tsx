/**
 * Modal component for displaying detailed audit entry information.
 */

"use client";

import { useEffect, useState } from "react";
import { AuditEntryDetail, getAuditEntry } from "@/lib/api/audit";
import { AnimatedBadge, AnimatedProgress, LoadingSkeleton } from "@/components/animated";
import { motion, AnimatePresence } from "framer-motion";

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
    <AnimatePresence>
      {entryId && (
        <div
          className="fixed inset-0 z-50 overflow-hidden"
          onClick={onClose}
          aria-labelledby="modal-title"
          role="dialog"
          aria-modal="true"
        >
          {/* Background overlay with blur */}
          <motion.div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />

          {/* Modal panel */}
          <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
            <motion.div
              className="w-screen max-w-2xl"
              onClick={(e) => e.stopPropagation()}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 30,
              }}
            >
              <div className="flex h-full flex-col overflow-y-scroll bg-white dark:bg-gray-900 shadow-xl">
                {/* Header with glass effect */}
                <div className="bg-[var(--glass-bg-solid)] backdrop-blur-[var(--glass-blur)] px-6 py-6 border-b border-[var(--glass-border)]">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h2
                        id="modal-title"
                        className="text-lg font-medium text-gray-900 dark:text-white"
                      >
                        Audit Entry Details
                      </h2>
                      {entry && (
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                          {new Date(entry.timestamp).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <motion.button
                      onClick={onClose}
                      className="ml-3 rounded-md bg-white dark:bg-gray-800 text-gray-400 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
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
                    </motion.button>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 px-6 py-6">
                  {loading && (
                    <div className="space-y-4">
                      <LoadingSkeleton variant="text" height={24} width="60%" />
                      <LoadingSkeleton variant="rect" height={100} />
                      <LoadingSkeleton variant="rect" height={150} />
                      <LoadingSkeleton variant="rect" height={150} />
                    </div>
                  )}

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-md bg-red-50 dark:bg-red-900/20 p-4"
                    >
                      <div className="flex">
                        <div className="ml-3">
                          <h3 className="text-sm font-medium text-red-800 dark:text-red-300">
                            Error
                          </h3>
                          <div className="mt-2 text-sm text-red-700 dark:text-red-400">
                            {error}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {entry && !loading && !error && (
                    <motion.div
                      className="space-y-6"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.1 }}
                    >
                      {/* Overview */}
                      <div>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                          Overview
                        </h3>
                        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                          <div>
                            <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              Agent
                            </dt>
                            <dd className="mt-1">
                              <AnimatedBadge variant="info">
                                {formatAgentType(entry.agent_type)}
                              </AnimatedBadge>
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              Action
                            </dt>
                            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                              {entry.action}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              Status
                            </dt>
                            <dd className="mt-1">
                              {entry.escalated ? (
                                <AnimatedBadge variant="warning">
                                  👤 Escalated
                                </AnimatedBadge>
                              ) : (
                                <AnimatedBadge variant="success">
                                  ⚡ Auto
                                </AnimatedBadge>
                              )}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">
                              Authorized By
                            </dt>
                            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                              {entry.authorized_by}
                            </dd>
                          </div>
                        </dl>
                      </div>

                      {/* Confidence */}
                      {confidenceDisplay && (
                        <div className="rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-medium text-gray-900 dark:text-white">
                              Confidence Level
                            </span>
                            <AnimatedBadge
                              variant={
                                entry.confidence >= 0.9
                                  ? "success"
                                  : entry.confidence >= 0.7
                                  ? "warning"
                                  : "error"
                              }
                            >
                              {Math.round(entry.confidence * 100)}% - {confidenceDisplay.label}
                            </AnimatedBadge>
                          </div>
                          <AnimatedProgress
                            value={entry.confidence * 100}
                            max={100}
                            showPercentage={false}
                            variant="gradient"
                          />
                        </div>
                      )}

                      {/* Decision */}
                      <div>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                          Decision
                        </h3>
                        <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                          {entry.decision}
                        </p>
                      </div>

                      {/* Input */}
                      <div>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                          Input
                        </h3>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-64 overflow-y-auto">
                          <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                            {entry.input_full}
                          </pre>
                        </div>
                      </div>

                      {/* Output */}
                      <div>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                          Output
                        </h3>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-64 overflow-y-auto">
                          <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                            {entry.output_full}
                          </pre>
                        </div>
                      </div>

                      {/* Metadata */}
                      {entry.metadata && Object.keys(entry.metadata).length > 0 && (
                        <div>
                          <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                            Metadata
                          </h3>
                          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-48 overflow-y-auto">
                            <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                              {JSON.stringify(entry.metadata, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Trace Link */}
                      {entry.trace_id && (
                        <div>
                          <motion.a
                            href={`https://cloud.langfuse.com/trace/${entry.trace_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                            whileHover={{ x: 5 }}
                            transition={{ duration: 0.2 }}
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
                          </motion.a>
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
}
