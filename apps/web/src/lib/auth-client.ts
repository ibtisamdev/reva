import { jwtClient, organizationClient } from 'better-auth/client/plugins';
import { createAuthClient } from 'better-auth/react';

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
  plugins: [organizationClient(), jwtClient()],
});

export const { signIn, signUp, signOut, useSession, organization } = authClient;

/**
 * Get the current JWT token for API authentication.
 * Returns null if not authenticated.
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const response = await authClient.token();
    return response.data?.token ?? null;
  } catch {
    return null;
  }
}
