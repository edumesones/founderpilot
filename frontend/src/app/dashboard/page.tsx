/**
 * Main dashboard page.
 */

"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { useAuth } from "@/lib/hooks/useAuth";
import { UsageWidget } from "@/components/usage";
import { AnimatedCard, AnimatedButton } from "@/components/animated";
import { PageTransition } from "@/components/layout";

function DashboardContent() {
  const { user, logout } = useAuth();

  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        {/* Header with glass effect */}
        <header className="bg-[var(--glass-bg-solid)] backdrop-blur-[var(--glass-blur)] border-b border-[var(--glass-border)] shadow-[var(--shadow-glass)]">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              FounderPilot
            </h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {user?.name || user?.email}
              </span>
              {user?.picture_url && (
                <img
                  src={user.picture_url}
                  alt={user.name}
                  className="w-8 h-8 rounded-full"
                />
              )}
              <AnimatedButton
                variant="ghost"
                size="sm"
                onClick={logout}
              >
                Sign out
              </AnimatedButton>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-4 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Welcome card */}
            <AnimatedCard
              variant="glass"
              className="lg:col-span-2 p-8"
              hover
            >
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Welcome to FounderPilot!
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Your AI-powered productivity assistant is ready to help.
              </p>

              <div className="flex gap-4">
                <AnimatedButton
                  variant="primary"
                  onClick={() => (window.location.href = "/dashboard/connections")}
                >
                  Manage Connections
                </AnimatedButton>
                <AnimatedButton
                  variant="outline"
                  onClick={() => (window.location.href = "/dashboard/audit")}
                >
                  View Audit Log
                </AnimatedButton>
              </div>
            </AnimatedCard>

            {/* Usage widget */}
            <div className="lg:col-span-1">
              <UsageWidget />
            </div>
          </div>
        </main>
      </div>
    </PageTransition>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}
