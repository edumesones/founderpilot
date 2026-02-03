/**
 * Usage widget for displaying current usage statistics and alerts.
 * Auto-refreshes every 30 seconds to show real-time usage.
 */

"use client";

import { useEffect, useState } from "react";
import { getUsageStats, UsageStatsResponse, AgentUsage } from "@/lib/api/usage";

interface UsageBarProps {
  label: string;
  usage: AgentUsage;
  icon: string;
}

function UsageBar({ label, usage, icon }: UsageBarProps) {
  const { count, limit, percentage, overage, overage_cost_cents } = usage;

  // Determine color based on percentage
  const getColor = () => {
    if (percentage >= 100) return "bg-red-500";
    if (percentage >= 80) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getTextColor = () => {
    if (percentage >= 100) return "text-red-600";
    if (percentage >= 80) return "text-yellow-600";
    return "text-green-600";
  };

  // Cap percentage at 100 for display
  const displayPercentage = Math.min(percentage, 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <span className="font-medium text-gray-700 capitalize">{label}</span>
        </div>
        <div className="text-sm">
          <span className={`font-semibold ${getTextColor()}`}>
            {count.toLocaleString()}
          </span>
          <span className="text-gray-400"> / {limit.toLocaleString()}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="relative w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor()} transition-all duration-500 ease-out`}
          style={{ width: `${displayPercentage}%` }}
        />
      </div>

      {/* Percentage and overage info */}
      <div className="flex items-center justify-between text-xs">
        <span className={`font-medium ${getTextColor()}`}>{percentage}% used</span>
        {overage > 0 && (
          <span className="text-red-600 font-medium">
            +{overage.toLocaleString()} overage (${(overage_cost_cents / 100).toFixed(2)})
          </span>
        )}
      </div>
    </div>
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
      <div className="bg-white rounded-xl shadow p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-white rounded-xl shadow p-6">
        <div className="text-center py-12">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={fetchUsage}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Try again
          </button>
        </div>
      </div>
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
    <div className="bg-white rounded-xl shadow p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Usage This Month</h2>
          <p className="text-sm text-gray-500 mt-1">
            {stats.plan.name} Plan • Period ends{" "}
            {new Date(stats.period_end).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })}
          </p>
        </div>
        <button
          onClick={fetchUsage}
          className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
          title="Refresh usage"
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
        </button>
      </div>

      {/* Alerts */}
      {visibleAlerts.length > 0 && (
        <div className="space-y-2">
          {visibleAlerts.map((alert) => (
            <div
              key={alert.agent}
              className={`
                flex items-start justify-between gap-3 p-4 rounded-lg
                ${
                  alert.level === "error"
                    ? "bg-red-50 border border-red-200"
                    : "bg-yellow-50 border border-yellow-200"
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
                      alert.level === "error" ? "text-red-900" : "text-yellow-900"
                    }`}
                  >
                    {agentLabels[alert.agent as keyof typeof agentLabels]}
                  </p>
                  <p
                    className={`text-sm mt-1 ${
                      alert.level === "error" ? "text-red-700" : "text-yellow-700"
                    }`}
                  >
                    {alert.message}
                  </p>
                </div>
              </div>
              <button
                onClick={() => dismissAlert(alert.agent)}
                className={`text-sm ${
                  alert.level === "error"
                    ? "text-red-400 hover:text-red-600"
                    : "text-yellow-400 hover:text-yellow-600"
                }`}
              >
                ✕
              </button>
            </div>
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
        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              Total overage charges this month
            </span>
            <span className="text-lg font-bold text-red-600">
              ${(stats.total_overage_cost_cents / 100).toFixed(2)}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            These charges will be added to your next invoice
          </p>
        </div>
      )}
    </div>
  );
}

export default UsageWidget;
