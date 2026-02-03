/**
 * Usage widget for displaying current usage statistics and alerts.
 * Auto-refreshes every 30 seconds to show real-time usage.
 */

"use client";

import { useEffect, useState } from "react";
import { getUsageStats, UsageStatsResponse, AgentUsage } from "@/lib/api/usage";
import { AnimatedCard, AnimatedProgress, AnimatedBadge, LoadingSkeleton } from "@/components/animated";
import { motion } from "framer-motion";

interface UsageBarProps {
  label: string;
  usage: AgentUsage;
  icon: string;
}

function UsageBar({ label, usage, icon }: UsageBarProps) {
  const { count, limit, percentage, overage, overage_cost_cents } = usage;

  const getTextColor = () => {
    if (percentage >= 100) return "text-red-600 dark:text-red-400";
    if (percentage >= 80) return "text-yellow-600 dark:text-yellow-400";
    return "text-green-600 dark:text-green-400";
  };

  return (
    <motion.div
      className="space-y-2"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <span className="font-medium text-gray-700 dark:text-gray-300 capitalize">
            {label}
          </span>
        </div>
        <div className="text-sm">
          <span className={`font-semibold ${getTextColor()}`}>
            {count.toLocaleString()}
          </span>
          <span className="text-gray-400 dark:text-gray-500">
            {" "}/ {limit.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Animated Progress bar */}
      <AnimatedProgress
        value={percentage}
        max={100}
        showPercentage={false}
        variant="gradient"
      />

      {/* Percentage and overage info */}
      <div className="flex items-center justify-between text-xs">
        <span className={`font-medium ${getTextColor()}`}>
          {percentage}% used
        </span>
        {overage > 0 && (
          <AnimatedBadge variant="error">
            +{overage.toLocaleString()} overage ($
            {(overage_cost_cents / 100).toFixed(2)})
          </AnimatedBadge>
        )}
      </div>
    </motion.div>
  );
}

export function UsageWidget() {
  const [stats, setStats] = useState<UsageStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  const fetchUsage = async () => {
    try {
      const data = await getUsageStats();
      setStats(data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch usage stats:", err);
      setError(err.response?.data?.detail || "Failed to load usage data");
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and auto-refresh every 30 seconds
  useEffect(() => {
    fetchUsage();
    const interval = setInterval(fetchUsage, 30000);
    return () => clearInterval(interval);
  }, []);

  const dismissAlert = (agent: string) => {
    setDismissedAlerts((prev) => new Set(prev).add(agent));
  };

  // Loading state
  if (loading) {
    return (
      <AnimatedCard variant="glass" className="space-y-4">
        <LoadingSkeleton variant="text" width="60%" height={24} />
        <LoadingSkeleton variant="text" width="40%" height={16} />
        <div className="space-y-4 mt-6">
          <LoadingSkeleton variant="rect" height={60} />
          <LoadingSkeleton variant="rect" height={60} />
          <LoadingSkeleton variant="rect" height={60} />
        </div>
      </AnimatedCard>
    );
  }

  // Error state
  if (error) {
    return (
      <AnimatedCard variant="glass" className="text-center py-12">
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <motion.button
          onClick={fetchUsage}
          className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          Try again
        </motion.button>
      </AnimatedCard>
    );
  }

  if (!stats) return null;

  const agentLabels = {
    inbox: "Inbox Pilot",
    invoice: "Invoice Pilot",
    meeting: "Meeting Pilot",
  };

  const agentIcons = {
    inbox: "📧",
    invoice: "🧾",
    meeting: "📅",
  };

  // Filter alerts that haven't been dismissed
  const visibleAlerts = stats.alerts.filter(
    (alert) => !dismissedAlerts.has(alert.agent)
  );

  return (
    <AnimatedCard variant="glass" className="space-y-6" hover={false}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Usage This Month
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {stats.plan.name} Plan • Period ends{" "}
            {new Date(stats.period_end).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
        <motion.button
          onClick={fetchUsage}
          className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          title="Refresh usage"
          whileHover={{ scale: 1.1, rotate: 180 }}
          whileTap={{ scale: 0.9 }}
          transition={{ duration: 0.3 }}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </motion.button>
      </div>

      {/* Alerts */}
      {visibleAlerts.length > 0 && (
        <div className="space-y-2">
          {visibleAlerts.map((alert) => (
            <motion.div
              key={alert.agent}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className={`
                flex items-start justify-between gap-3 p-4 rounded-lg
                ${
                  alert.level === "error"
                    ? "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                    : "bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800"
                }
              `}
            >
              <div className="flex items-start gap-3 flex-1">
                <span className="text-xl">
                  {alert.level === "error" ? "⚠️" : "⚡"}
                </span>
                <div className="flex-1">
                  <p
                    className={`text-sm font-medium ${
                      alert.level === "error"
                        ? "text-red-900 dark:text-red-200"
                        : "text-yellow-900 dark:text-yellow-200"
                    }`}
                  >
                    {agentLabels[alert.agent as keyof typeof agentLabels]}
                  </p>
                  <p
                    className={`text-sm mt-1 ${
                      alert.level === "error"
                        ? "text-red-700 dark:text-red-300"
                        : "text-yellow-700 dark:text-yellow-300"
                    }`}
                  >
                    {alert.message}
                  </p>
                </div>
              </div>
              <motion.button
                onClick={() => dismissAlert(alert.agent)}
                className={`text-sm ${
                  alert.level === "error"
                    ? "text-red-400 hover:text-red-600"
                    : "text-yellow-400 hover:text-yellow-600"
                }`}
                whileHover={{ scale: 1.2 }}
                whileTap={{ scale: 0.8 }}
              >
                ✕
              </motion.button>
            </motion.div>
          ))}
        </div>
      )}

      {/* Usage bars */}
      <div className="space-y-6">
        <UsageBar
          label={agentLabels.inbox}
          usage={stats.usage.inbox}
          icon={agentIcons.inbox}
        />
        <UsageBar
          label={agentLabels.invoice}
          usage={stats.usage.invoice}
          icon={agentIcons.invoice}
        />
        <UsageBar
          label={agentLabels.meeting}
          usage={stats.usage.meeting}
          icon={agentIcons.meeting}
        />
      </div>

      {/* Total overage cost */}
      {stats.total_overage_cost_cents > 0 && (
        <motion.div
          className="pt-4 border-t border-gray-200 dark:border-gray-700"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Total overage charges this month
            </span>
            <motion.span
              className="text-lg font-bold text-red-600 dark:text-red-400"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              ${(stats.total_overage_cost_cents / 100).toFixed(2)}
            </motion.span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            These charges will be added to your next invoice
          </p>
        </motion.div>
      )}
    </AnimatedCard>
  );
}

export default UsageWidget;
