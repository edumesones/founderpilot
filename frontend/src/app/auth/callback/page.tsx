/**
 * OAuth callback handler page.
 * Handles redirect from Google OAuth and shows loading/error states.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { AnimatedCard, AnimatedButton, LoadingSkeleton } from "@/components/animated";
import { motion } from "framer-motion";

export default function CallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { fetchUser, user, initialized } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check for error in query params
    const errorParam = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (errorParam) {
      setError(errorDescription || errorParam);
      return;
    }

    // Fetch user after OAuth callback
    fetchUser();
  }, [searchParams, fetchUser]);

  useEffect(() => {
    if (initialized && user) {
      // Redirect based on onboarding status
      if (user.onboarding_completed) {
        router.replace("/dashboard");
      } else {
        router.replace("/onboarding");
      }
    }
  }, [initialized, user, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
        <AnimatedCard variant="glass" className="w-full max-w-md p-8 text-center" hover>
          <motion.div
            className="w-12 h-12 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center"
            animate={{
              rotate: [0, 10, -10, 0],
            }}
            transition={{
              duration: 0.5,
              repeat: 3,
            }}
          >
            <svg
              className="w-6 h-6 text-red-600 dark:text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </motion.div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Authentication Failed
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">{error}</p>
          <AnimatedButton
            variant="primary"
            onClick={() => router.push("/auth/login")}
          >
            Back to Login
          </AnimatedButton>
        </AnimatedCard>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950">
      <AnimatedCard variant="glass" className="w-full max-w-md p-8">
        <div className="space-y-4">
          <LoadingSkeleton variant="circle" width={48} height={48} className="mx-auto" />
          <LoadingSkeleton variant="text" width="80%" className="mx-auto" />
          <LoadingSkeleton variant="text" width="60%" className="mx-auto" />
        </div>
        <motion.p
          className="mt-6 text-gray-600 dark:text-gray-400 text-center"
          animate={{
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
          }}
        >
          Completing sign in...
        </motion.p>
      </AnimatedCard>
    </div>
  );
}
