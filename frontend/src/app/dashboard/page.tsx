/**
 * Main dashboard page.
 */

"use client";

import { useEffect } from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { useAuth } from "@/lib/hooks/useAuth";
import { UsageWidget } from "@/components/usage";

function DashboardContent() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">FounderPilot</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {user?.name || user?.email}
            </span>
            {user?.picture_url && (
              <img
                src={user.picture_url}
                alt={user.name}
                className="w-8 h-8 rounded-full"
              />
            )}
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Welcome card */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Welcome to FounderPilot!
            </h2>
            <p className="text-gray-600 mb-6">
              Your AI-powered productivity assistant is ready to help.
            </p>

            <div className="flex gap-4">
              <a
                href="/dashboard/connections"
                className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                Manage Connections
              </a>
              <a
                href="/dashboard/audit"
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                View Audit Log
              </a>
            </div>
          </div>

          {/* Usage widget */}
          <div className="lg:col-span-1">
            <UsageWidget />
          </div>
        </div>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}
