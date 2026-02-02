import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:8000';

// Mock auth-client to avoid importing better-auth in tests
vi.mock('@/lib/auth-client', () => ({
  getAuthToken: vi.fn().mockResolvedValue('test-token'),
  signIn: { email: vi.fn(), social: vi.fn() },
  signUp: { email: vi.fn() },
  signOut: vi.fn(),
  useSession: vi.fn(),
  organization: {},
  authClient: {},
}));

// Import after mocking
const { apiGet, apiPost, apiPatch, apiDelete, ApiError } = await import('../client');

describe('ApiError', () => {
  it('should store status and code', () => {
    const error = new ApiError('Not found', 404, 'NOT_FOUND');
    expect(error.message).toBe('Not found');
    expect(error.status).toBe(404);
    expect(error.code).toBe('NOT_FOUND');
    expect(error.name).toBe('ApiError');
  });

  it('should work without code', () => {
    const error = new ApiError('Server error', 500);
    expect(error.code).toBeUndefined();
  });
});

describe('apiGet', () => {
  it('should fetch data and include auth header', async () => {
    let capturedHeaders: Headers | undefined;
    server.use(
      http.get(`${API_BASE}/api/v1/test`, ({ request }) => {
        capturedHeaders = request.headers;
        return HttpResponse.json({ ok: true });
      })
    );

    const result = await apiGet('/api/v1/test');
    expect(result).toEqual({ ok: true });
    expect(capturedHeaders?.get('authorization')).toBe('Bearer test-token');
  });

  it('should append query params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/items`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [] });
      })
    );

    await apiGet('/api/v1/items', { params: { page: 1, limit: 10 } });
    expect(capturedUrl).toContain('page=1');
    expect(capturedUrl).toContain('limit=10');
  });

  it('should skip undefined params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/items`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [] });
      })
    );

    await apiGet('/api/v1/items', { params: { page: 1, search: undefined } });
    expect(capturedUrl).toContain('page=1');
    expect(capturedUrl).not.toContain('search');
  });

  it('should throw ApiError on non-ok response', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/missing`, () => {
        return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
      })
    );

    await expect(apiGet('/api/v1/missing')).rejects.toThrow(ApiError);
    await expect(apiGet('/api/v1/missing')).rejects.toMatchObject({
      status: 404,
      message: 'Not found',
    });
  });

  it('should handle non-JSON error responses', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/crash`, () => {
        return new HttpResponse('Internal Server Error', { status: 500 });
      })
    );

    await expect(apiGet('/api/v1/crash')).rejects.toMatchObject({
      status: 500,
      message: 'HTTP 500',
    });
  });
});

describe('apiPost', () => {
  it('should send JSON body with content-type header', async () => {
    let capturedBody: unknown;
    let capturedContentType: string | null = null;
    server.use(
      http.post(`${API_BASE}/api/v1/stores`, async ({ request }) => {
        capturedBody = await request.json();
        capturedContentType = request.headers.get('content-type');
        return HttpResponse.json({ id: '1', name: 'New' });
      })
    );

    await apiPost('/api/v1/stores', { body: { name: 'New' } });
    expect(capturedBody).toEqual({ name: 'New' });
    expect(capturedContentType).toBe('application/json');
  });

  it('should handle 204 No Content', async () => {
    server.use(
      http.post(`${API_BASE}/api/v1/action`, () => {
        return new HttpResponse(null, { status: 204 });
      })
    );

    const result = await apiPost('/api/v1/action');
    expect(result).toBeUndefined();
  });
});

describe('apiPatch', () => {
  it('should send PATCH request with body', async () => {
    let capturedMethod = '';
    server.use(
      http.patch(`${API_BASE}/api/v1/stores/1`, async ({ request }) => {
        capturedMethod = request.method;
        return HttpResponse.json({ id: '1', name: 'Updated' });
      })
    );

    const result = await apiPatch('/api/v1/stores/1', { body: { name: 'Updated' } });
    expect(capturedMethod).toBe('PATCH');
    expect(result).toEqual({ id: '1', name: 'Updated' });
  });
});

describe('apiDelete', () => {
  it('should send DELETE request', async () => {
    let capturedMethod = '';
    server.use(
      http.delete(`${API_BASE}/api/v1/stores/1`, ({ request }) => {
        capturedMethod = request.method;
        return new HttpResponse(null, { status: 204 });
      })
    );

    await apiDelete('/api/v1/stores/1');
    expect(capturedMethod).toBe('DELETE');
  });
});
