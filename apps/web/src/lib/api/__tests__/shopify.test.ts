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

const {
  getShopifyStatus,
  disconnectShopify,
  triggerShopifySync,
  getShopifyInstallUrl,
  shopifyKeys,
} = await import('../shopify');

describe('getShopifyStatus', () => {
  it('should send store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/shopify/status`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          platform: 'shopify',
          platform_domain: 'test.myshopify.com',
          status: 'active',
          last_synced_at: null,
          product_count: 0,
        });
      })
    );

    await getShopifyStatus('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });
});

describe('disconnectShopify', () => {
  it('should POST with store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.post(`${API_BASE}/api/v1/shopify/disconnect`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ status: 'completed', message: 'Disconnected' });
      })
    );

    await disconnectShopify('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });
});

describe('triggerShopifySync', () => {
  it('should POST with store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.post(`${API_BASE}/api/v1/shopify/sync`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ status: 'completed', message: 'Synced' });
      })
    );

    await triggerShopifySync('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });
});

describe('getShopifyInstallUrl', () => {
  it('should send store_id and shop params and return install_url', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/shopify/install-url`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ install_url: 'https://test.myshopify.com/admin/oauth/authorize' });
      })
    );

    const result = await getShopifyInstallUrl('store-1', 'test.myshopify.com');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedUrl).toContain('shop=test.myshopify.com');
    expect(result).toBe('https://test.myshopify.com/admin/oauth/authorize');
  });
});

describe('shopifyKeys', () => {
  it('should produce correct key arrays', () => {
    expect(shopifyKeys.all).toEqual(['shopify']);
    expect(shopifyKeys.status('s1')).toEqual(['shopify', 'status', 's1']);
  });
});
