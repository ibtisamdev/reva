import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/test/mocks/server';

const API_BASE = 'http://localhost:8000';

vi.mock('@/lib/auth-client', () => ({
  getAuthToken: vi.fn().mockResolvedValue('test-token'),
  signIn: { email: vi.fn(), social: vi.fn() },
  signUp: { email: vi.fn() },
  signOut: vi.fn(),
  useSession: vi.fn(),
  organization: {},
  authClient: {},
}));

const { getProducts, productKeys } = await import('../products');

describe('getProducts', () => {
  it('should send store_id and default pagination params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/products`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 0 });
      })
    );

    await getProducts('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedUrl).toContain('page=1');
    expect(capturedUrl).toContain('page_size=20');
  });

  it('should send custom page and pageSize params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/products`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 3, page_size: 10, pages: 0 });
      })
    );

    await getProducts('store-1', { page: 3, pageSize: 10 });
    expect(capturedUrl).toContain('page=3');
    expect(capturedUrl).toContain('page_size=10');
  });
});

describe('productKeys', () => {
  it('should produce correct key arrays', () => {
    expect(productKeys.all).toEqual(['products']);
    expect(productKeys.lists()).toEqual(['products', 'list']);
    expect(productKeys.list('s1', 2)).toEqual(['products', 'list', 's1', 2]);
  });
});
