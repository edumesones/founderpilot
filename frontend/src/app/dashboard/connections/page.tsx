/**
 * Connections management page.
 */

"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { ConnectionCard } from "@/components/connections/ConnectionCard";
import { useIntegrations } from "@/lib/hooks/useIntegrations";

function ConnectionsContent() {
  const {
    status,
    loading,
    fetchStatus,
    connectGmail,
    connectSlack,
    disconnectGmail,
    disconnectSlack,
  } = useIntegrations();

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  if (loading && !status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-700">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="text-xl font-bold text-gray-900">Connections</h1>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <p className="text-gray-600 mb-6">
          Manage your connected accounts and integrations.
        </p>

        <div className="space-y-4">
          {/* Gmail */}
          {status?.gmail && (
            <ConnectionCard
              integration={status.gmail}
              icon={
                <svg className="w-7 h-7" viewBox="0 0 24 24">
                  <path
                    d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 010 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"
                    fill="#EA4335"
                  />
                </svg>
              }
              color="bg-red-100"
              onConnect={connectGmail}
              onDisconnect={disconnectGmail}
              loading={loading}
            />
          )}

          {/* Slack */}
          {status?.slack && (
            <ConnectionCard
              integration={status.slack}
              icon={
                <svg className="w-7 h-7" viewBox="0 0 24 24">
                  <path
                    d="M5.042 15.165a2.528 2.528 0 01-2.52 2.523A2.528 2.528 0 010 15.165a2.527 2.527 0 012.522-2.52h2.52v2.52zm1.271 0a2.527 2.527 0 012.521-2.52 2.527 2.527 0 012.521 2.52v6.313A2.528 2.528 0 018.834 24a2.528 2.528 0 01-2.521-2.522v-6.313z"
                    fill="#E01E5A"
                  />
                  <path
                    d="M8.834 5.042a2.528 2.528 0 01-2.521-2.52A2.528 2.528 0 018.834 0a2.528 2.528 0 012.521 2.522v2.52H8.834zm0 1.271a2.528 2.528 0 012.521 2.521 2.528 2.528 0 01-2.521 2.521H2.522A2.528 2.528 0 010 8.834a2.528 2.528 0 012.522-2.521h6.312z"
                    fill="#36C5F0"
                  />
                  <path
                    d="M18.956 8.834a2.528 2.528 0 012.522-2.521A2.528 2.528 0 0124 8.834a2.528 2.528 0 01-2.522 2.521h-2.522V8.834zm-1.27 0a2.528 2.528 0 01-2.522 2.521 2.528 2.528 0 01-2.522-2.521V2.522A2.528 2.528 0 0115.164 0a2.528 2.528 0 012.522 2.522v6.312z"
                    fill="#2EB67D"
                  />
                  <path
                    d="M15.164 18.956a2.528 2.528 0 012.522 2.522A2.528 2.528 0 0115.164 24a2.528 2.528 0 01-2.522-2.522v-2.522h2.522zm0-1.27a2.528 2.528 0 01-2.522-2.522 2.528 2.528 0 012.522-2.522h6.314A2.528 2.528 0 0124 15.164a2.528 2.528 0 01-2.522 2.522h-6.314z"
                    fill="#ECB22E"
                  />
                </svg>
              }
              color="bg-purple-100"
              onConnect={connectSlack}
              onDisconnect={disconnectSlack}
              loading={loading}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default function ConnectionsPage() {
  return (
    <AuthGuard>
      <ConnectionsContent />
    </AuthGuard>
  );
}
