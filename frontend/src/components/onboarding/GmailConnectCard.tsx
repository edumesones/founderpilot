/**
 * Gmail connection card for onboarding.
 */

"use client";

import { useIntegrations } from "@/lib/hooks/useIntegrations";

interface GmailConnectCardProps {
  showScopes?: boolean;
}

export function GmailConnectCard({ showScopes = true }: GmailConnectCardProps) {
  const { status, loading, connectGmail, disconnectGmail } = useIntegrations();
  const isConnected = status?.gmail.connected ?? false;

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-start gap-4">
        {/* Gmail Icon */}
        <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg
            className="w-7 h-7"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 010 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"
              fill="#EA4335"
            />
          </svg>
        </div>

        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">Gmail</h3>
          <p className="text-gray-600 text-sm mt-1">
            {isConnected
              ? `Connected as ${status?.gmail.email}`
              : "Connect your Gmail to let FounderPilot help manage your inbox"}
          </p>

          {/* Scopes explanation */}
          {showScopes && !isConnected && (
            <div className="mt-4 bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 font-medium mb-2">
                We&apos;ll request access to:
              </p>
              <ul className="text-xs text-gray-600 space-y-1">
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Read your emails
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Send emails on your behalf
                </li>
                <li className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Manage labels
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Action Button */}
      <div className="mt-6">
        {isConnected ? (
          <button
            onClick={disconnectGmail}
            disabled={loading}
            className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {loading ? "Disconnecting..." : "Disconnect Gmail"}
          </button>
        ) : (
          <button
            onClick={connectGmail}
            disabled={loading}
            className="w-full px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {loading ? "Connecting..." : "Connect Gmail"}
          </button>
        )}
      </div>
    </div>
  );
}

export default GmailConnectCard;
