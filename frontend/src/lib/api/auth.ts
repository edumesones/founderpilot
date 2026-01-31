/**
 * Auth API methods.
 */

import apiClient from "./client";

export interface User {
  id: string;
  email: string;
  name: string;
  picture_url: string | null;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  redirect_url: string;
}

/**
 * Get Google OAuth login URL.
 */
export async function getGoogleAuthUrl(): Promise<string> {
  const response = await apiClient.get<AuthResponse>("/api/v1/auth/google");
  return response.data.redirect_url;
}

/**
 * Get current authenticated user.
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>("/api/v1/auth/me");
  return response.data;
}

/**
 * Refresh access token.
 */
export async function refreshToken(): Promise<void> {
  await apiClient.post("/api/v1/auth/refresh");
}

/**
 * Logout current user.
 */
export async function logout(): Promise<void> {
  await apiClient.post("/api/v1/auth/logout");
}
