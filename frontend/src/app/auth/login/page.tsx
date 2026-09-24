/**
 * Login page with Google OAuth button.
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { GoogleLoginButton } from "@/components/auth/GoogleLoginButton";
import { useAuth } from "@/lib/hooks/useAuth";
import { AnimatedCard, LoadingSkeleton } from "@/components/animated";
import { PageTransition } from "@/components/layout";
import { motion } from "framer-motion";

export default function LoginPage() {
  const router = useRouter();
  const { user, initialized, fetchUser, error, clearError } = useAuth();

  useEffect(() => {
    if (!initialized) {
      fetchUser();
    }
  }, [initialized, fetchUser]);

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

  // Show loading while checking auth
  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <AnimatedCard variant="glass" className="w-full max-w-md">
          <LoadingSkeleton variant="text" width="60%" height={32} />
          <LoadingSkeleton variant="text" width="80%" height={16} className="mt-2" />
          <div className="mt-8 space-y-4">
            <LoadingSkeleton variant="rect" height={48} />
            <LoadingSkeleton variant="text" count={2} />
          </div>
        </AnimatedCard>
      </div>
    );
  }

  // If already logged in, don't show login form
  if (user) {
    return null;
  }

  return (
    <PageTransition>
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
        <div className="w-full max-w-md">
          {/* Logo with bounce animation */}
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 20,
            }}
          >
            <motion.h1
              className="text-3xl font-bold text-gray-900 dark:text-white"
              animate={{
                y: [0, -10, 0],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            >
              FounderPilot
            </motion.h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              AI-powered productivity for founders
            </p>
          </motion.div>

          {/* Login Card with glass effect */}
          <AnimatedCard variant="glass" className="p-8" hover>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white text-center mb-6">
              Sign in to continue
            </h2>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
                  <motion.button
                    onClick={clearError}
                    className="text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </motion.button>
                </div>
              </motion.div>
            )}

            {/* Google Login Button */}
            <GoogleLoginButton className="w-full" />

            {/* Terms */}
            <p className="mt-6 text-xs text-gray-500 dark:text-gray-400 text-center">
              By continuing, you agree to our{" "}
              <a href="#" className="underline hover:text-gray-700 dark:hover:text-gray-300">
                Terms of Service
              </a>{" "}
              and{" "}
              <a href="#" className="underline hover:text-gray-700 dark:hover:text-gray-300">
                Privacy Policy
              </a>
            </p>
          </AnimatedCard>
        </div>
      </div>
    </PageTransition>
  );
}
