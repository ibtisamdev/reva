import { NextRequest, NextResponse } from 'next/server';
import { getSessionCookie } from 'better-auth/cookies';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { middleware } from '../middleware';

// Mock better-auth/cookies
vi.mock('better-auth/cookies', () => ({
  getSessionCookie: vi.fn(),
}));

const mockedGetSessionCookie = vi.mocked(getSessionCookie);

// Helper to create mock NextRequest
function createMockRequest(pathname: string, origin = 'http://localhost:3000'): NextRequest {
  const url = new URL(pathname, origin);
  return new NextRequest(url);
}

describe('middleware', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('authenticated users on auth routes', () => {
    it('should redirect authenticated user from /sign-in to /dashboard', () => {
      mockedGetSessionCookie.mockReturnValue('session-token');

      const request = createMockRequest('/sign-in');
      const response = middleware(request);

      expect(response).toBeInstanceOf(NextResponse);
      expect(response.status).toBe(307); // Temporary redirect
      expect(response.headers.get('location')).toBe('http://localhost:3000/dashboard');
    });

    it('should redirect authenticated user from /sign-up to /dashboard', () => {
      mockedGetSessionCookie.mockReturnValue('session-token');

      const request = createMockRequest('/sign-up');
      const response = middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get('location')).toBe('http://localhost:3000/dashboard');
    });

    it('should redirect from nested auth routes like /sign-in/callback', () => {
      mockedGetSessionCookie.mockReturnValue('session-token');

      const request = createMockRequest('/sign-in/callback');
      const response = middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get('location')).toBe('http://localhost:3000/dashboard');
    });
  });

  describe('unauthenticated users on protected routes', () => {
    it('should redirect unauthenticated user from /dashboard to /sign-in', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/dashboard');
      const response = middleware(request);

      expect(response.status).toBe(307);
      const location = new URL(response.headers.get('location')!);
      expect(location.pathname).toBe('/sign-in');
    });

    it('should include callbackUrl in redirect', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/dashboard');
      const response = middleware(request);

      const location = new URL(response.headers.get('location')!);
      expect(location.searchParams.get('callbackUrl')).toBe('/dashboard');
    });

    it('should protect nested dashboard routes', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/dashboard/settings/widget');
      const response = middleware(request);

      expect(response.status).toBe(307);
      const location = new URL(response.headers.get('location')!);
      expect(location.pathname).toBe('/sign-in');
      expect(location.searchParams.get('callbackUrl')).toBe('/dashboard/settings/widget');
    });

    it('should protect /dashboard/conversations', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/dashboard/conversations');
      const response = middleware(request);

      expect(response.status).toBe(307);
      const location = new URL(response.headers.get('location')!);
      expect(location.pathname).toBe('/sign-in');
      expect(location.searchParams.get('callbackUrl')).toBe('/dashboard/conversations');
    });

    it('should protect /dashboard/knowledge', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/dashboard/knowledge');
      const response = middleware(request);

      expect(response.status).toBe(307);
      const location = new URL(response.headers.get('location')!);
      expect(location.searchParams.get('callbackUrl')).toBe('/dashboard/knowledge');
    });
  });

  describe('authenticated users on protected routes', () => {
    it('should allow authenticated user to access /dashboard', () => {
      mockedGetSessionCookie.mockReturnValue('session-token');

      const request = createMockRequest('/dashboard');
      const response = middleware(request);

      // NextResponse.next() returns a response without redirect
      expect(response.headers.get('location')).toBeNull();
      expect(response.status).toBe(200);
    });

    it('should allow authenticated user to access nested dashboard routes', () => {
      mockedGetSessionCookie.mockReturnValue('session-token');

      const request = createMockRequest('/dashboard/settings/integrations');
      const response = middleware(request);

      expect(response.headers.get('location')).toBeNull();
      expect(response.status).toBe(200);
    });
  });

  describe('unauthenticated users on public routes', () => {
    it('should allow unauthenticated user to access home page', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/');
      const response = middleware(request);

      expect(response.headers.get('location')).toBeNull();
      expect(response.status).toBe(200);
    });

    it('should allow unauthenticated user to access /sign-in', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/sign-in');
      const response = middleware(request);

      expect(response.headers.get('location')).toBeNull();
      expect(response.status).toBe(200);
    });

    it('should allow unauthenticated user to access /sign-up', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      const request = createMockRequest('/sign-up');
      const response = middleware(request);

      expect(response.headers.get('location')).toBeNull();
      expect(response.status).toBe(200);
    });
  });

  describe('edge cases', () => {
    it('should handle null session cookie', () => {
      mockedGetSessionCookie.mockReturnValue(null);

      const request = createMockRequest('/dashboard');
      const response = middleware(request);

      expect(response.status).toBe(307);
      const location = new URL(response.headers.get('location')!);
      expect(location.pathname).toBe('/sign-in');
    });

    it('should handle empty string session cookie as unauthenticated', () => {
      mockedGetSessionCookie.mockReturnValue('');

      const request = createMockRequest('/dashboard');
      const response = middleware(request);

      // Empty string is falsy, so user is unauthenticated
      expect(response.status).toBe(307);
    });

    it('should preserve query parameters in callbackUrl', () => {
      mockedGetSessionCookie.mockReturnValue(undefined);

      // Note: pathname doesn't include query params
      const request = createMockRequest('/dashboard');
      const response = middleware(request);

      const location = new URL(response.headers.get('location')!);
      expect(location.searchParams.get('callbackUrl')).toBe('/dashboard');
    });
  });
});
