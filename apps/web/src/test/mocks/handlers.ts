import { http, HttpResponse } from 'msw';

import type { StoreListResponse } from '@/lib/api/types';

import {
  mockStores,
  mockConversations,
  mockConversationDetail,
  mockKnowledgeArticles,
  mockKnowledgeArticleDetail,
  mockStoreSettings,
  mockIngestionResponse,
  mockPaginatedResponse,
  mockProducts,
  mockShopifyConnection,
  mockSyncStatus,
  mockWismoSummary,
  mockWismoTrend,
  mockWismoInquiries,
} from './data';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export { mockStores };

export const handlers = [
  // Stores
  http.get(`${API_BASE}/api/v1/stores`, () => {
    return HttpResponse.json({
      items: mockStores,
      total: mockStores.length,
    } satisfies StoreListResponse);
  }),

  http.get(`${API_BASE}/api/v1/stores/:storeId`, ({ params }) => {
    const store = mockStores.find((s) => s.id === params.storeId);
    if (!store) return HttpResponse.json({ detail: 'Not found' }, { status: 404 });
    return HttpResponse.json(store);
  }),

  http.post(`${API_BASE}/api/v1/stores`, async ({ request }) => {
    const body = (await request.json()) as { name: string };
    return HttpResponse.json({
      ...mockStores[0],
      id: 'store-new',
      name: body.name,
    });
  }),

  http.patch(`${API_BASE}/api/v1/stores/:storeId`, async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const store = mockStores.find((s) => s.id === params.storeId);
    return HttpResponse.json({ ...store, ...body });
  }),

  http.delete(`${API_BASE}/api/v1/stores/:storeId`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Store Settings
  http.get(`${API_BASE}/api/v1/stores/settings`, () => {
    return HttpResponse.json(mockStoreSettings);
  }),

  http.patch(`${API_BASE}/api/v1/stores/settings`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...mockStoreSettings, ...body });
  }),

  // Conversations
  http.get(`${API_BASE}/api/v1/chat/conversations`, () => {
    return HttpResponse.json(mockPaginatedResponse(mockConversations));
  }),

  http.get(`${API_BASE}/api/v1/chat/conversations/:conversationId`, () => {
    return HttpResponse.json(mockConversationDetail);
  }),

  http.patch(`${API_BASE}/api/v1/chat/conversations/:conversationId/status`, async ({ request }) => {
    const body = (await request.json()) as { status: string };
    return HttpResponse.json({ ...mockConversations[0], status: body.status });
  }),

  // Knowledge
  http.get(`${API_BASE}/api/v1/knowledge`, () => {
    return HttpResponse.json(mockPaginatedResponse(mockKnowledgeArticles));
  }),

  http.get(`${API_BASE}/api/v1/knowledge/:articleId`, () => {
    return HttpResponse.json(mockKnowledgeArticleDetail);
  }),

  http.post(`${API_BASE}/api/v1/knowledge`, () => {
    return HttpResponse.json(mockIngestionResponse);
  }),

  http.patch(`${API_BASE}/api/v1/knowledge/:articleId`, async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...mockKnowledgeArticles[0], ...body, id: params.articleId });
  }),

  http.delete(`${API_BASE}/api/v1/knowledge/:articleId`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Products
  http.get(`${API_BASE}/api/v1/products`, () => {
    return HttpResponse.json(mockPaginatedResponse(mockProducts));
  }),

  // Shopify
  http.get(`${API_BASE}/api/v1/shopify/status`, () => {
    return HttpResponse.json(mockShopifyConnection);
  }),

  http.post(`${API_BASE}/api/v1/shopify/disconnect`, () => {
    return HttpResponse.json(mockSyncStatus);
  }),

  http.post(`${API_BASE}/api/v1/shopify/sync`, () => {
    return HttpResponse.json(mockSyncStatus);
  }),

  http.get(`${API_BASE}/api/v1/shopify/install-url`, () => {
    return HttpResponse.json({ install_url: 'https://test.myshopify.com/admin/oauth/authorize?client_id=test' });
  }),

  // Knowledge URL/PDF
  http.post(`${API_BASE}/api/v1/knowledge/url`, () => {
    return HttpResponse.json(mockIngestionResponse);
  }),

  http.post(`${API_BASE}/api/v1/knowledge/pdf`, () => {
    return HttpResponse.json(mockIngestionResponse);
  }),

  // WISMO Analytics
  http.get(`${API_BASE}/api/v1/analytics/wismo/summary`, () => {
    return HttpResponse.json(mockWismoSummary);
  }),

  http.get(`${API_BASE}/api/v1/analytics/wismo/trend`, () => {
    return HttpResponse.json(mockWismoTrend);
  }),

  http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, () => {
    return HttpResponse.json(mockPaginatedResponse(mockWismoInquiries));
  }),
];
