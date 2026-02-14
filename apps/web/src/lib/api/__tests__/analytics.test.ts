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

const { getWismoSummary, getWismoTrend, getWismoInquiries, analyticsKeys } =
  await import('../analytics');

describe('getWismoSummary', () => {
  it('should send correct URL with store_id', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/summary`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          total_inquiries: 10,
          resolution_rate: 0.8,
          avg_per_day: 1.0,
          period_days: 30,
        });
      })
    );

    await getWismoSummary('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });

  it('should include days param when provided', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/summary`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          total_inquiries: 5,
          resolution_rate: 0.6,
          avg_per_day: 0.7,
          period_days: 7,
        });
      })
    );

    await getWismoSummary('store-1', 7);
    expect(capturedUrl).toContain('days=7');
  });
});

describe('getWismoTrend', () => {
  it('should send correct URL with store_id', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/trend`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json([]);
      })
    );

    await getWismoTrend('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });

  it('should include days param when provided', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/trend`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json([]);
      })
    );

    await getWismoTrend('store-1', 14);
    expect(capturedUrl).toContain('days=14');
  });
});

describe('getWismoInquiries', () => {
  it('should send correct URL with store_id', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 1 });
      })
    );

    await getWismoInquiries('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });

  it('should include page and pageSize params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 2, page_size: 10, pages: 1 });
      })
    );

    await getWismoInquiries('store-1', { page: 2, pageSize: 10 });
    expect(capturedUrl).toContain('page=2');
    expect(capturedUrl).toContain('page_size=10');
  });

  it('should work without options', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 1 });
      })
    );

    await getWismoInquiries('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
    // Should not contain page/page_size when no options provided
    expect(capturedUrl).not.toContain('page=');
    expect(capturedUrl).not.toContain('page_size=');
  });
});

describe('analyticsKeys', () => {
  it('should produce correct key arrays', () => {
    expect(analyticsKeys.all).toEqual(['analytics']);
    expect(analyticsKeys.wismo()).toEqual(['analytics', 'wismo']);
    expect(analyticsKeys.wismoSummary('s1')).toEqual(['analytics', 'wismo', 'summary', 's1', undefined]);
    expect(analyticsKeys.wismoSummary('s1', 7)).toEqual(['analytics', 'wismo', 'summary', 's1', 7]);
    expect(analyticsKeys.wismoTrend('s1')).toEqual(['analytics', 'wismo', 'trend', 's1', undefined]);
    expect(analyticsKeys.wismoInquiries('s1', 2)).toEqual(['analytics', 'wismo', 'inquiries', 's1', 2]);
  });
});
