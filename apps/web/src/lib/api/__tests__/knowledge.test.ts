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
  getKnowledgeArticles,
  getKnowledgeArticle,
  createKnowledgeArticle,
  updateKnowledgeArticle,
  deleteKnowledgeArticle,
  createKnowledgeFromUrl,
  createKnowledgeFromPdf,
  knowledgeKeys,
} = await import('../knowledge');
const { ApiError } = await import('../client');

describe('getKnowledgeArticles', () => {
  it('should send store_id and default pagination params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/knowledge`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 0 });
      })
    );

    await getKnowledgeArticles('store-1');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedUrl).toContain('page=1');
    expect(capturedUrl).toContain('page_size=20');
  });

  it('should send optional contentType, page, pageSize params', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/knowledge`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, page: 2, page_size: 10, pages: 0 });
      })
    );

    await getKnowledgeArticles('store-1', { contentType: 'faq', page: 2, pageSize: 10 });
    expect(capturedUrl).toContain('content_type=faq');
    expect(capturedUrl).toContain('page=2');
    expect(capturedUrl).toContain('page_size=10');
  });
});

describe('getKnowledgeArticle', () => {
  it('should send articleId in URL and store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.get(`${API_BASE}/api/v1/knowledge/:id`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json({
          id: 'art-1', store_id: 'store-1', title: 'T', content: 'C',
          content_type: 'faq', source_url: null, chunks_count: 1,
          created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
          chunks: [],
        });
      })
    );

    await getKnowledgeArticle('art-1', 'store-1');
    expect(capturedUrl).toContain('/api/v1/knowledge/art-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });
});

describe('createKnowledgeArticle', () => {
  it('should POST with store_id param and body', async () => {
    let capturedUrl = '';
    let capturedBody: unknown;
    server.use(
      http.post(`${API_BASE}/api/v1/knowledge`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = await request.json();
        return HttpResponse.json({
          article_id: 'art-1', title: 'T', chunks_count: 3,
          status: 'completed', message: 'Done',
        });
      })
    );

    const data = { title: 'T', content: 'C', content_type: 'faq' as const };
    await createKnowledgeArticle('store-1', data);
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedBody).toEqual(data);
  });
});

describe('updateKnowledgeArticle', () => {
  it('should PATCH with articleId in URL and store_id param', async () => {
    let capturedUrl = '';
    let capturedBody: unknown;
    server.use(
      http.patch(`${API_BASE}/api/v1/knowledge/:id`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = await request.json();
        return HttpResponse.json({
          id: 'art-1', store_id: 'store-1', title: 'Updated', content: 'C',
          content_type: 'faq', source_url: null, chunks_count: 1,
          created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
        });
      })
    );

    await updateKnowledgeArticle('art-1', 'store-1', { title: 'Updated' });
    expect(capturedUrl).toContain('/api/v1/knowledge/art-1');
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedBody).toEqual({ title: 'Updated' });
  });
});

describe('deleteKnowledgeArticle', () => {
  it('should DELETE with articleId in URL and store_id param', async () => {
    let capturedUrl = '';
    server.use(
      http.delete(`${API_BASE}/api/v1/knowledge/:id`, ({ request }) => {
        capturedUrl = request.url;
        return new HttpResponse(null, { status: 204 });
      })
    );

    await deleteKnowledgeArticle('art-1', 'store-1');
    expect(capturedUrl).toContain('/api/v1/knowledge/art-1');
    expect(capturedUrl).toContain('store_id=store-1');
  });
});

describe('deleteKnowledgeArticle error', () => {
  it('should throw ApiError on 404', async () => {
    server.use(
      http.delete(`${API_BASE}/api/v1/knowledge/:id`, () => {
        return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
      })
    );

    await expect(deleteKnowledgeArticle('missing', 'store-1')).rejects.toThrow(ApiError);
  });
});

describe('knowledgeKeys', () => {
  it('should produce correct key arrays', () => {
    expect(knowledgeKeys.all).toEqual(['knowledge']);
    expect(knowledgeKeys.lists()).toEqual(['knowledge', 'list']);
    expect(knowledgeKeys.list('s1', { contentType: 'faq' })).toEqual([
      'knowledge', 'list', 's1', { contentType: 'faq' },
    ]);
    expect(knowledgeKeys.details()).toEqual(['knowledge', 'detail']);
    expect(knowledgeKeys.detail('s1', 'a1')).toEqual(['knowledge', 'detail', 's1', 'a1']);
  });
});

describe('createKnowledgeFromUrl', () => {
  it('should POST with store_id param and body', async () => {
    let capturedUrl = '';
    let capturedBody: unknown;
    server.use(
      http.post(`${API_BASE}/api/v1/knowledge/url`, async ({ request }) => {
        capturedUrl = request.url;
        capturedBody = await request.json();
        return HttpResponse.json({
          article_id: 'art-url',
          title: 'From URL',
          chunks_count: 5,
          status: 'completed',
          message: 'Done',
        });
      })
    );

    const data = { url: 'https://example.com', content_type: 'page' as const };
    await createKnowledgeFromUrl('store-1', data);
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedBody).toEqual(data);
  });
});

describe('createKnowledgeFromPdf', () => {
  it('should POST FormData with store_id param and auth header', async () => {
    let capturedUrl = '';
    let capturedAuth = '';
    server.use(
      http.post(`${API_BASE}/api/v1/knowledge/pdf`, ({ request }) => {
        capturedUrl = request.url;
        capturedAuth = request.headers.get('Authorization') || '';
        return HttpResponse.json({
          article_id: 'art-pdf',
          title: 'From PDF',
          chunks_count: 10,
          status: 'completed',
          message: 'Done',
        });
      })
    );

    const formData = new FormData();
    formData.append('file', new Blob(['pdf content'], { type: 'application/pdf' }), 'test.pdf');
    formData.append('content_type', 'guide');

    await createKnowledgeFromPdf('store-1', formData);
    expect(capturedUrl).toContain('store_id=store-1');
    expect(capturedAuth).toBe('Bearer test-token');
  });

  it('should throw on non-ok response', async () => {
    server.use(
      http.post(`${API_BASE}/api/v1/knowledge/pdf`, () => {
        return HttpResponse.json({ detail: 'File too large' }, { status: 413 });
      })
    );

    const formData = new FormData();
    formData.append('file', new Blob(['x']), 'test.pdf');

    await expect(createKnowledgeFromPdf('store-1', formData)).rejects.toThrow('File too large');
  });
});
