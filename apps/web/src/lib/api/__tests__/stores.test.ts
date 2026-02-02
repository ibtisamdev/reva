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
  getStores,
  getStore,
  createStore,
  updateStore,
  deleteStore,
  getStoreSettings,
  updateStoreSettings,
  defaultWidgetSettings,
  storeKeys,
} = await import('../stores');
const { ApiError } = await import('../client');

describe('getStores', () => {
  it('should GET /api/v1/stores', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/stores`, () => {
        return HttpResponse.json({ items: [{ id: 's1', name: 'S' }], total: 1 });
      })
    );

    const result = await getStores();
    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(1);
  });
});

describe('getStore', () => {
  it('should GET /api/v1/stores/:storeId', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/stores/:storeId`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ id: 'store-1', name: 'Test' });
      })
    );

    await getStore('store-1');
    expect(capturedUrl).toContain('/api/v1/stores/store-1');
  });
});

describe('createStore', () => {
  it('should POST with body', async () => {
    let capturedBody: unknown;
    server.use(
      http.post(`${API_BASE}/api/v1/stores`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ id: 'new', name: 'New Store' });
      })
    );

    await createStore({ name: 'New Store' });
    expect(capturedBody).toEqual({ name: 'New Store' });
  });
});

describe('updateStore', () => {
  it('should PATCH with storeId and body', async () => {
    let capturedUrl = '';
    let capturedBody: unknown;
    server.use(
      http.patch(`${API_BASE}/api/v1/stores/:storeId`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = await request.json();
        return HttpResponse.json({ id: 'store-1', name: 'Updated' });
      })
    );

    await updateStore('store-1', { name: 'Updated' });
    expect(capturedUrl).toContain('/api/v1/stores/store-1');
    expect(capturedBody).toEqual({ name: 'Updated' });
  });
});

describe('deleteStore', () => {
  it('should DELETE with storeId', async () => {
    let capturedUrl = '';
    server.use(
      http.delete(`${API_BASE}/api/v1/stores/:storeId`, ({ request }) => {
        capturedUrl = request.url;
        return new HttpResponse(null, { status: 204 });
      })
    );

    await deleteStore('store-1');
    expect(capturedUrl).toContain('/api/v1/stores/store-1');
  });
});

describe('getStoreSettings', () => {
  it('should return settings with store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/stores/settings`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          widget: { primary_color: '#ff0000', welcome_message: 'Hi', position: 'bottom-right', agent_name: 'Bot' },
        });
      })
    );

    const result = await getStoreSettings('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(result.widget.primary_color).toBe('#ff0000');
  });

  it('should return defaults on 404', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/stores/settings`, () => {
        return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
      })
    );

    const result = await getStoreSettings('store-1');
    expect(result).toEqual(defaultWidgetSettings);
  });

  it('should re-throw non-404 errors', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/stores/settings`, () => {
        return HttpResponse.json({ detail: 'Server error' }, { status: 500 });
      })
    );

    await expect(getStoreSettings('store-1')).rejects.toThrow(ApiError);
  });
});

describe('updateStoreSettings', () => {
  it('should PATCH with store_id param and body', async () => {
    let capturedUrl = '';
    let capturedBody: unknown;
    server.use(
      http.patch(`${API_BASE}/api/v1/stores/settings`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = await request.json();
        return HttpResponse.json({
          widget: { primary_color: '#ff0000', welcome_message: 'Hi', position: 'bottom-right', agent_name: 'Bot' },
        });
      })
    );

    await updateStoreSettings('store-1', { widget: { primary_color: '#ff0000' } });
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedBody).toEqual({ widget: { primary_color: '#ff0000' } });
  });
});

describe('storeKeys', () => {
  it('should produce correct key arrays', () => {
    expect(storeKeys.all).toEqual(['stores']);
    expect(storeKeys.list()).toEqual(['stores', 'list']);
    expect(storeKeys.detail('s1')).toEqual(['stores', 'detail', 's1']);
    expect(storeKeys.settings('s1')).toEqual(['stores', 'settings', 's1']);
  });
});
