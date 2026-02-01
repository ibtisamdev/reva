/**
 * Base API client for communicating with the FastAPI backend
 */

import { getAuthToken } from '@/lib/auth-client';

import type { ErrorResponse } from './types';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get authorization headers for API requests.
 * Fetches the JWT token from Better Auth and returns it as a Bearer token.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    let errorCode: string | undefined;

    try {
      const errorData = (await response.json()) as ErrorResponse;
      errorMessage = errorData.detail || errorData.error || errorMessage;
      errorCode = errorData.code;
    } catch {
      // Response is not JSON
    }

    throw new ApiError(errorMessage, response.status, errorCode);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(`${API_BASE_URL}${endpoint}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

export async function apiGet<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = buildUrl(endpoint, options?.params);
  const authHeaders = await getAuthHeaders();

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      ...authHeaders,
      ...options?.headers,
    },
    credentials: options?.credentials ?? 'include',
    cache: options?.cache,
    next: options?.next,
  });

  return handleResponse<T>(response);
}

export async function apiPost<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = buildUrl(endpoint, options?.params);
  const authHeaders = await getAuthHeaders();

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    body: options?.body ? JSON.stringify(options.body) : undefined,
    credentials: options?.credentials ?? 'include',
    cache: options?.cache,
    next: options?.next,
  });

  return handleResponse<T>(response);
}

export async function apiPatch<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = buildUrl(endpoint, options?.params);
  const authHeaders = await getAuthHeaders();

  const response = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    body: options?.body ? JSON.stringify(options.body) : undefined,
    credentials: options?.credentials ?? 'include',
    cache: options?.cache,
    next: options?.next,
  });

  return handleResponse<T>(response);
}

export async function apiDelete<T = void>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = buildUrl(endpoint, options?.params);
  const authHeaders = await getAuthHeaders();

  const response = await fetch(url, {
    method: 'DELETE',
    headers: {
      ...authHeaders,
      ...options?.headers,
    },
    credentials: options?.credentials ?? 'include',
    cache: options?.cache,
    next: options?.next,
  });

  return handleResponse<T>(response);
}
