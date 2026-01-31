/**
 * OAuth callback handler page.
 * Handles redirect from Google OAuth and shows loading/error states.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";

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
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8 text-center">
          <div className="w-12 h-12 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-red-600"
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
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Authentication Failed
          </h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push("/auth/login")}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      <p className="mt-4 text-gray-600">Completing sign in...</p>
    </div>
  );
}
