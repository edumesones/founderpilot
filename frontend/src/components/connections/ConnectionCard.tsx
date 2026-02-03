/**
 * Connection card for displaying integration status.
 */

"use client";

import { IntegrationStatus } from "@/lib/api/integrations";
import { AnimatedCard } from "@/components/animated/AnimatedCard";
import { AnimatedButton } from "@/components/animated/AnimatedButton";
import { AnimatedBadge } from "@/components/animated/AnimatedBadge";

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
    <AnimatedCard variant="glass">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 ${color} rounded-lg flex items-center justify-center`}>
            {icon}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white capitalize">
              {integration.provider}
            </h3>
            {integration.connected ? (
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {integration.email && <p>{integration.email}</p>}
                {integration.workspace_name && <p>{integration.workspace_name}</p>}
                {integration.connected_at && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    Connected {formatDate(integration.connected_at)}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">Not connected</p>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <AnimatedBadge
          variant={integration.connected ? "success" : "default"}
          pulse={integration.connected}
        >
          {integration.connected ? "Connected" : "Disconnected"}
        </AnimatedBadge>
      </div>

      {/* Action button */}
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
        {integration.connected ? (
          <AnimatedButton
            variant="ghost"
            size="sm"
            onClick={onDisconnect}
            disabled={loading}
            loading={loading}
            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            Disconnect
          </AnimatedButton>
        ) : (
          <AnimatedButton
            variant="outline"
            size="sm"
            onClick={onConnect}
            disabled={loading}
            loading={loading}
          >
            Connect
          </AnimatedButton>
        )}
      </div>
    </AnimatedCard>
  );
}

export default ConnectionCard;
