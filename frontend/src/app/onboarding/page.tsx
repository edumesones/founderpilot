/**
 * Main onboarding page.
 * Routes to current step based on progress.
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { OnboardingStepper } from "@/components/onboarding/OnboardingStepper";
import { GmailConnectCard } from "@/components/onboarding/GmailConnectCard";
import { SlackConnectCard } from "@/components/onboarding/SlackConnectCard";
import { useAuth } from "@/lib/hooks/useAuth";
import { useIntegrations } from "@/lib/hooks/useIntegrations";
import { completeOnboarding, skipOnboarding } from "@/lib/api/onboarding";

function OnboardingContent() {
  const router = useRouter();
  const { user } = useAuth();
  const { status, loading, fetchStatus } = useIntegrations();

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    // Redirect to dashboard if onboarding is already complete
    if (user?.onboarding_completed) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const handleComplete = async () => {
    try {
      const result = await completeOnboarding();
      router.push(result.redirect_url);
    } catch (error) {
      console.error("Failed to complete onboarding:", error);
    }
  };

  const handleSkip = async () => {
    try {
      const result = await skipOnboarding();
      router.push(result.redirect_url);
    } catch (error) {
      console.error("Failed to skip onboarding:", error);
    }
  };

  // Build steps for stepper
  const steps = [
    {
      step: "google",
      name: "Google Account",
      completed: true, // Always completed if user is authenticated
      current: false,
    },
    {
      step: "gmail",
      name: "Connect Gmail",
      completed: status?.gmail.connected ?? false,
      current: !status?.gmail.connected,
    },
    {
      step: "slack",
      name: "Connect Slack",
      completed: status?.slack.connected ?? false,
      current: (status?.gmail.connected ?? false) && !(status?.slack.connected ?? false),
    },
  ];

  const currentStep = status?.gmail.connected
    ? status?.slack.connected
      ? 3
      : 2
    : 1;

  const allConnected = status?.all_connected ?? false;

  if (loading && !status) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome to FounderPilot
          </h1>
          <p className="mt-2 text-gray-600">
            Connect your accounts to get started
          </p>
        </div>

        {/* Stepper */}
        <div className="mb-12">
          <OnboardingStepper steps={steps} currentStep={currentStep} />
        </div>

        {/* Integration Cards */}
        <div className="space-y-6">
          <GmailConnectCard />
          <SlackConnectCard />
        </div>

        {/* Actions */}
        <div className="mt-8 flex flex-col gap-4">
          <button
            onClick={handleComplete}
            disabled={loading}
            className={`
              w-full px-6 py-3 rounded-lg font-medium transition-colors
              ${
                allConnected
                  ? "bg-green-500 text-white hover:bg-green-600"
                  : "bg-gray-900 text-white hover:bg-gray-800"
              }
              disabled:opacity-50
            `}
          >
            {allConnected ? "Complete Setup" : "Continue to Dashboard"}
          </button>

          {!allConnected && (
            <button
              onClick={handleSkip}
              className="text-gray-500 hover:text-gray-700 text-sm"
            >
              Skip for now - I&apos;ll connect later
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <AuthGuard>
      <OnboardingContent />
    </AuthGuard>
  );
}
