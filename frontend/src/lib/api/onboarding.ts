/**
 * Onboarding API methods.
 */

import apiClient from "./client";

export interface OnboardingStep {
  step: string;
  name: string;
  completed: boolean;
  current: boolean;
}

export interface OnboardingStatus {
  completed: boolean;
  current_step: number;
  steps: OnboardingStep[];
}

export interface OnboardingCompleteResponse {
  message: string;
  redirect_url: string;
}

/**
 * Get current onboarding status.
 */
export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const response = await apiClient.get<OnboardingStatus>(
    "/api/v1/onboarding/status"
  );
  return response.data;
}

/**
 * Complete the onboarding process.
 */
export async function completeOnboarding(): Promise<OnboardingCompleteResponse> {
  const response = await apiClient.post<OnboardingCompleteResponse>(
    "/api/v1/onboarding/complete"
  );
  return response.data;
}

/**
 * Skip onboarding entirely.
 */
export async function skipOnboarding(): Promise<OnboardingCompleteResponse> {
  const response = await apiClient.post<OnboardingCompleteResponse>(
    "/api/v1/onboarding/skip"
  );
  return response.data;
}
