/**
 * Connection card for displaying integration status.
 */

"use client";

import { IntegrationStatus } from "@/lib/api/integrations";

interface ConnectionCardProps {
  integration: IntegrationStatus;
  icon: React.ReactNode;
  color: string;
  onConnect: () => void;
  onDisconnect: () => void;
  loading?: boolean;
}

export function ConnectionCard({
  integration,
  icon,
  color,
  onConnect,
  onDisconnect,
  loading = false,
}: ConnectionCardProps) {
  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="bg-white rounded-xl shadow p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 ${color} rounded-lg flex items-center justify-center`}>
            {icon}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 capitalize">
              {integration.provider}
            </h3>
            {integration.connected ? (
              <div className="text-sm text-gray-600">
                {integration.email && <p>{integration.email}</p>}
                {integration.workspace_name && <p>{integration.workspace_name}</p>}
                {integration.connected_at && (
                  <p className="text-xs text-gray-400 mt-1">
                    Connected {formatDate(integration.connected_at)}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Not connected</p>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <span
            className={`
              w-2 h-2 rounded-full
              ${integration.connected ? "bg-green-500" : "bg-gray-300"}
            `}
          />
          <span className={`text-sm ${integration.connected ? "text-green-600" : "text-gray-400"}`}>
            {integration.connected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Action button */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        {integration.connected ? (
          <button
            onClick={onDisconnect}
            disabled={loading}
            className="text-sm text-red-600 hover:text-red-700 disabled:opacity-50"
          >
            {loading ? "Disconnecting..." : "Disconnect"}
          </button>
        ) : (
          <button
            onClick={onConnect}
            disabled={loading}
            className="text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            {loading ? "Connecting..." : "Connect"}
          </button>
        )}
      </div>
    </div>
  );
}

export default ConnectionCard;
