import { test as base, expect, type Page, type Route } from '@playwright/test';

const API_BASE = 'http://localhost:8000';

// Mock data mirrors src/test/mocks/data.ts (unit tests).
// Keep both in sync when updating schemas.
const MOCK_STORES = {
  items: [
    {
      id: 'store-1',
      organization_id: 'org-1',
      name: 'Test Store',
      email: 'test@example.com',
      plan: 'free',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'store-2',
      organization_id: 'org-1',
      name: 'Second Store',
      email: null,
      plan: 'free',
      is_active: true,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ],
  total: 2,
};

const MOCK_CONVERSATIONS = [
  {
    id: 'conv-1',
    store_id: 'store-1',
    session_id: 'sess-abcdef12',
    channel: 'widget',
    status: 'active',
    customer_email: 'customer@example.com',
    customer_name: 'Jane Doe',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:05:00Z',
  },
  {
    id: 'conv-2',
    store_id: 'store-1',
    session_id: 'sess-99887766',
    channel: 'email',
    status: 'resolved',
    customer_email: 'other@example.com',
    customer_name: null,
    created_at: '2024-01-14T08:00:00Z',
    updated_at: '2024-01-14T09:00:00Z',
  },
];

const MOCK_MESSAGES = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'How do I return an item?',
    sources: null,
    tokens_used: 10,
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'You can return items within 30 days of purchase.',
    sources: [
      { title: 'Return Policy', url: 'https://example.com/returns', snippet: 'Items can be returned within 30 days.', chunk_id: 'chunk-1' },
      { title: 'FAQ', url: null, snippet: 'See our return policy for details.', chunk_id: null },
    ],
    tokens_used: 25,
    created_at: '2024-01-15T10:00:05Z',
  },
];

const MOCK_CONVERSATION_DETAIL = {
  ...MOCK_CONVERSATIONS[0],
  messages: MOCK_MESSAGES,
};

const MOCK_ARTICLES = [
  {
    id: 'article-1',
    store_id: 'store-1',
    title: 'Return Policy',
    content: 'Items can be returned within 30 days of purchase.',
    content_type: 'policy',
    source_url: 'https://example.com/returns',
    chunks_count: 3,
    created_at: '2024-01-10T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
  },
  {
    id: 'article-2',
    store_id: 'store-1',
    title: 'Shipping FAQ',
    content: 'We ship worldwide.',
    content_type: 'faq',
    source_url: null,
    chunks_count: 0,
    created_at: '2024-01-11T00:00:00Z',
    updated_at: '2024-01-11T00:00:00Z',
  },
];

const MOCK_ARTICLE_DETAIL = {
  ...MOCK_ARTICLES[0],
  chunks: [
    { id: 'chunk-1', chunk_index: 0, content: 'Items can be returned within 30 days.', token_count: 8, has_embedding: true },
  ],
};

const MOCK_STORE_SETTINGS = {
  widget: {
    primary_color: '#0d9488',
    welcome_message: 'Hi! How can I help you today?',
    position: 'bottom-right',
    agent_name: 'Reva Support',
  },
};

const MOCK_INGESTION_RESPONSE = {
  article_id: 'article-new',
  title: 'New Article',
  chunks_count: 2,
  status: 'completed',
  message: 'Article processed successfully',
};

const MOCK_PRODUCTS = [
  {
    id: 'prod-1',
    platform_product_id: '1001',
    title: 'Test Widget',
    description: 'A great widget',
    handle: 'test-widget',
    vendor: 'Acme',
    product_type: 'gadget',
    status: 'active',
    tags: ['test'],
    variants: [{ title: 'Default', price: '29.99', sku: 'TW-001', inventory_quantity: 10 }],
    images: [],
    synced_at: '2024-01-15T00:00:00Z',
    created_at: '2024-01-10T00:00:00Z',
  },
  {
    id: 'prod-2',
    platform_product_id: '1002',
    title: 'Plain Product',
    description: null,
    handle: 'plain-product',
    vendor: null,
    product_type: null,
    status: 'draft',
    tags: [],
    variants: [{ title: 'Default', price: '9.99', sku: null, inventory_quantity: null }],
    images: [],
    synced_at: null,
    created_at: '2024-01-11T00:00:00Z',
  },
];

const MOCK_SHOPIFY_CONNECTION = {
  platform: 'shopify',
  platform_domain: 'test-store.myshopify.com',
  status: 'active',
  last_synced_at: '2024-01-15T10:00:00Z',
  product_count: 42,
};

const MOCK_SYNC_STATUS = {
  status: 'completed',
  message: 'Sync completed successfully',
};

const MOCK_WISMO_SUMMARY = {
  total_inquiries: 42,
  resolution_rate: 0.85,
  avg_per_day: 1.4,
  period_days: 30,
};

const MOCK_WISMO_TREND = [
  { date: '2024-01-13', count: 2 },
  { date: '2024-01-14', count: 5 },
  { date: '2024-01-15', count: 3 },
];

const MOCK_WISMO_INQUIRIES = [
  {
    id: 'inq-1',
    customer_email: 'customer@example.com',
    order_number: '#1001',
    inquiry_type: 'order_status',
    order_status: 'paid',
    fulfillment_status: 'fulfilled',
    resolution: 'answered',
    created_at: '2024-01-15T10:00:00Z',
    resolved_at: '2024-01-15T10:01:00Z',
  },
  {
    id: 'inq-2',
    customer_email: 'another@example.com',
    order_number: '#1002',
    inquiry_type: 'tracking',
    order_status: 'paid',
    fulfillment_status: null,
    resolution: 'verification_failed',
    created_at: '2024-01-14T08:00:00Z',
    resolved_at: '2024-01-14T08:00:30Z',
  },
];

function paginated<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 20, pages: Math.max(1, Math.ceil(items.length / 20)) };
}

async function setupDefaultRoutes(page: Page) {
  // Stores
  await page.route(`**/api/v1/stores`, async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ json: MOCK_STORES });
    }
    if (method === 'POST') {
      const body = route.request().postDataJSON();
      return route.fulfill({ json: { ...MOCK_STORES.items[0], id: 'store-new', name: body?.name || 'New Store' } });
    }
    return route.continue();
  });

  await page.route(`**/api/v1/stores/settings**`, async (route) => {
    const method = route.request().method();
    if (method === 'GET') return route.fulfill({ json: MOCK_STORE_SETTINGS });
    if (method === 'PATCH') {
      const body = route.request().postDataJSON();
      return route.fulfill({ json: { ...MOCK_STORE_SETTINGS, ...body } });
    }
    return route.continue();
  });

  await page.route(new RegExp(`${API_BASE}/api/v1/stores/[^/?]+`), async (route) => {
    // Skip settings routes (handled above)
    if (route.request().url().includes('/settings')) return route.fallback();
    const method = route.request().method();
    if (method === 'GET') return route.fulfill({ json: MOCK_STORES.items[0] });
    if (method === 'PATCH') return route.fulfill({ json: MOCK_STORES.items[0] });
    if (method === 'DELETE') return route.fulfill({ status: 204, body: '' });
    return route.continue();
  });

  // Conversations
  await page.route(`**/api/v1/chat/conversations**`, async (route) => {
    const url = new URL(route.request().url());
    // Skip detail/status routes — handled by other handlers
    if (/\/conversations\/.+/.test(url.pathname)) return route.fallback();
    return route.fulfill({ json: paginated(MOCK_CONVERSATIONS) });
  });

  await page.route(new RegExp(`/api/v1/chat/conversations/[^/?]+/status`), async (route) => {
    const body = route.request().postDataJSON();
    return route.fulfill({ json: { ...MOCK_CONVERSATIONS[0], status: body?.status || 'resolved' } });
  });

  await page.route(new RegExp(`/api/v1/chat/conversations/[^/?]+(?:\\?|$)`), async (route) => {
    // Skip status routes
    if (route.request().url().includes('/status')) return route.fallback();
    return route.fulfill({ json: MOCK_CONVERSATION_DETAIL });
  });

  // Knowledge
  await page.route(`**/api/v1/knowledge**`, async (route) => {
    const url = new URL(route.request().url());
    // Skip sub-routes (url, pdf, article detail) — handled by other handlers
    if (/\/knowledge\/.+/.test(url.pathname)) return route.fallback();
    const method = route.request().method();
    if (method === 'GET') return route.fulfill({ json: paginated(MOCK_ARTICLES) });
    if (method === 'POST') return route.fulfill({ json: MOCK_INGESTION_RESPONSE });
    return route.continue();
  });

  await page.route(new RegExp(`/api/v1/knowledge/[^/?]+`), async (route) => {
    const method = route.request().method();
    if (method === 'GET') return route.fulfill({ json: MOCK_ARTICLE_DETAIL });
    if (method === 'DELETE') return route.fulfill({ status: 204, body: '' });
    if (method === 'PATCH') {
      const body = route.request().postDataJSON();
      return route.fulfill({ json: { ...MOCK_ARTICLES[0], ...body } });
    }
    return route.continue();
  });

  // Products
  await page.route(`**/api/v1/products**`, async (route) => {
    return route.fulfill({ json: paginated(MOCK_PRODUCTS) });
  });

  // Shopify
  await page.route(`**/api/v1/shopify/status**`, async (route) => {
    return route.fulfill({ json: MOCK_SHOPIFY_CONNECTION });
  });

  await page.route(`**/api/v1/shopify/disconnect**`, async (route) => {
    return route.fulfill({ json: MOCK_SYNC_STATUS });
  });

  await page.route(`**/api/v1/shopify/sync**`, async (route) => {
    return route.fulfill({ json: MOCK_SYNC_STATUS });
  });

  await page.route(`**/api/v1/shopify/install-url**`, async (route) => {
    return route.fulfill({ json: { install_url: 'https://test.myshopify.com/admin/oauth/authorize?client_id=test' } });
  });

  // Knowledge URL/PDF
  await page.route(`**/api/v1/knowledge/url**`, async (route) => {
    return route.fulfill({ json: MOCK_INGESTION_RESPONSE });
  });

  await page.route(`**/api/v1/knowledge/pdf**`, async (route) => {
    return route.fulfill({ json: MOCK_INGESTION_RESPONSE });
  });

  // WISMO Analytics
  await page.route(`**/api/v1/analytics/wismo/summary**`, async (route) => {
    return route.fulfill({ json: MOCK_WISMO_SUMMARY });
  });

  await page.route(`**/api/v1/analytics/wismo/trend**`, async (route) => {
    return route.fulfill({ json: MOCK_WISMO_TREND });
  });

  await page.route(`**/api/v1/analytics/wismo/inquiries**`, async (route) => {
    return route.fulfill({ json: paginated(MOCK_WISMO_INQUIRIES) });
  });

  // Auth token (JWT for API calls)
  await page.route('**/api/auth/token', async (route) => {
    return route.fulfill({ json: { token: 'mock-jwt-token' } });
  });

  // Auth session (for useSession hook)
  await page.route('**/api/auth/get-session', async (route) => {
    return route.fulfill({
      json: {
        session: { id: 'session-1', userId: 'user-1', expiresAt: '2099-01-01T00:00:00Z' },
        user: { id: 'user-1', name: 'E2E Test User', email: 'e2e@example.com', image: null, role: 'member' },
      },
    });
  });
}

// Export mock data for per-test overrides
export const mockData = {
  MOCK_STORES,
  MOCK_CONVERSATIONS,
  MOCK_CONVERSATION_DETAIL,
  MOCK_ARTICLES,
  MOCK_ARTICLE_DETAIL,
  MOCK_STORE_SETTINGS,
  MOCK_INGESTION_RESPONSE,
  MOCK_PRODUCTS,
  MOCK_SHOPIFY_CONNECTION,
  MOCK_SYNC_STATUS,
  MOCK_WISMO_SUMMARY,
  MOCK_WISMO_TREND,
  MOCK_WISMO_INQUIRIES,
  paginated,
};

export const test = base.extend<{ mockApi: Page }>({
  mockApi: async ({ page }, use) => {
    await setupDefaultRoutes(page);
    await use(page);
  },
});

export { expect };
