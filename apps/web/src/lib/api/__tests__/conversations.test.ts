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

const { getConversations, getConversation, updateConversationStatus, conversationKeys } =
  await import('../conversations');

describe('getConversations', () => {
  it('should send store_id and default pagination params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/chat/conversations`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pages: 0,
        });
      })
    );

    const result = await getConversations('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedUrl).toContain('page=1');
    expect(capturedUrl).toContain('page_size=20');
    expect(result.items).toEqual([]);
  });

  it('should send optional status, search, page, pageSize params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/chat/conversations`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [],
          total: 0,
          page: 2,
          page_size: 10,
          pages: 0,
        });
      })
    );

    await getConversations('store-1', {
      status: 'active',
      search: 'test',
      page: 2,
      pageSize: 10,
    });
    expect(capturedUrl).toContain('status=active');
    expect(capturedUrl).toContain('search=test');
    expect(capturedUrl).toContain('page=2');
    expect(capturedUrl).toContain('page_size=10');
  });

  it('should omit undefined optional params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/chat/conversations`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          pages: 0,
        });
      })
    );

    await getConversations('store-1', { status: undefined, search: undefined });
    expect(capturedUrl).not.toContain('status=');
    expect(capturedUrl).not.toContain('search=');
  });
});

describe('getConversation', () => {
  it('should send conversationId in URL and store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/chat/conversations/:id`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          id: 'conv-1',
          store_id: 'store-1',
          session_id: 'sess-1',
          channel: 'widget',
          status: 'active',
          customer_email: null,
          customer_name: null,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          messages: [],
        });
      })
    );

    await getConversation('conv-1', 'store-1');
    expect(capturedUrl).toContain('/api/v1/chat/conversations/conv-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });
});

describe('updateConversationStatus', () => {
  it('should send PATCH with status body and store_id param', async () => {
    let capturedUrl = '';
    let capturedBody: unknown;
    server.use(
      http.patch(`${API_BASE}/api/v1/chat/conversations/:id/status`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = await request.json();
        return HttpResponse.json({
          id: 'conv-1',
          store_id: 'store-1',
          session_id: 'sess-1',
          channel: 'widget',
          status: 'resolved',
          customer_email: null,
          customer_name: null,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        });
      })
    );

    await updateConversationStatus('conv-1', 'store-1', 'resolved');
    expect(capturedUrl).toContain('/api/v1/chat/conversations/conv-1/status');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedBody).toEqual({ status: 'resolved' });
  });
});

describe('conversationKeys', () => {
  it('should produce correct key arrays', () => {
    expect(conversationKeys.all).toEqual(['conversations']);
    expect(conversationKeys.lists()).toEqual(['conversations', 'list']);
    expect(conversationKeys.list('s1', { status: 'active' })).toEqual([
      'conversations',
      'list',
      's1',
      { status: 'active' },
    ]);
    expect(conversationKeys.details()).toEqual(['conversations', 'detail']);
    expect(conversationKeys.detail('s1', 'c1')).toEqual([
      'conversations',
      'detail',
      's1',
      'c1',
    ]);
  });
});
