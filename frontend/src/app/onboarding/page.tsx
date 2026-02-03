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
import { AnimatedCard, AnimatedButton, LoadingSkeleton } from "@/components/animated";
import { PageTransition, StaggerContainer } from "@/components/layout";
import { motion } from "framer-motion";

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
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <AnimatedCard variant="glass" className="w-full max-w-2xl p-8">
          <LoadingSkeleton variant="text" height={32} width="60%" className="mx-auto mb-4" />
          <LoadingSkeleton variant="text" height={16} width="40%" className="mx-auto mb-8" />
          <LoadingSkeleton variant="rect" height={100} count={3} />
        </AnimatedCard>
      </div>
    );
  }

  return (
    <PageTransition>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-12 px-4">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Welcome to FounderPilot
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              Connect your accounts to get started
            </p>
          </motion.div>

          {/* Stepper */}
          <div className="mb-12">
            <OnboardingStepper steps={steps} currentStep={currentStep} />
          </div>

          {/* Integration Cards with stagger */}
          <StaggerContainer className="space-y-6">
            <GmailConnectCard />
            <SlackConnectCard />
          </StaggerContainer>

          {/* Actions */}
          <motion.div
            className="mt-8 flex flex-col gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <AnimatedButton
              variant={allConnected ? "primary" : "primary"}
              size="lg"
              onClick={handleComplete}
              disabled={loading}
              loading={loading}
              className="w-full"
            >
              {allConnected ? "Complete Setup ✨" : "Continue to Dashboard"}
            </AnimatedButton>

            {!allConnected && (
              <motion.button
                onClick={handleSkip}
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 text-sm"
                whileHover={{ scale: 1.02 }}
              >
                Skip for now - I&apos;ll connect later
              </motion.button>
            )}
          </motion.div>
        </div>
      </div>
    </PageTransition>
  );
}

export default function OnboardingPage() {
  return (
    <AuthGuard>
      <OnboardingContent />
    </AuthGuard>
  );
}
