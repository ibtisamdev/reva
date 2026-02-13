import type {
  Conversation,
  ConversationDetail,
  DailyCount,
  Message,
  KnowledgeArticle,
  KnowledgeArticleDetail,
  OrderInquiry,

  Store,
  WidgetSettings,
  StoreSettings,
  IngestionResponse,
  PaginatedResponse,
  Product,
  ShopifyConnection,
  SyncStatus,
  WismoSummary,
} from '@/lib/api/types';

export const mockStores: Store[] = [
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
];

export const mockMessages: Message[] = [
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
      {
        title: 'Return Policy',
        url: 'https://example.com/returns',
        snippet: 'Items can be returned within 30 days.',
        chunk_id: 'chunk-1',
      },
      {
        title: 'FAQ',
        url: null,
        snippet: 'See our return policy for details.',
        chunk_id: null,
      },
    ],
    tokens_used: 25,
    created_at: '2024-01-15T10:00:05Z',
  },
  {
    id: 'msg-3',
    role: 'system',
    content: 'Conversation started',
    sources: null,
    tokens_used: null,
    created_at: '2024-01-15T09:59:59Z',
  },
];

export const mockConversation: Conversation = {
  id: 'conv-1',
  store_id: 'store-1',
  session_id: 'sess-abcdef12',
  channel: 'widget',
  status: 'active',
  customer_email: 'customer@example.com',
  customer_name: 'Jane Doe',
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:05:00Z',
};

export const mockConversationDetail: ConversationDetail = {
  ...mockConversation,
  messages: mockMessages,
};

export const mockConversations: Conversation[] = [
  mockConversation,
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

export const mockKnowledgeArticle: KnowledgeArticle = {
  id: 'article-1',
  store_id: 'store-1',
  title: 'Return Policy',
  content: 'Items can be returned within 30 days of purchase.',
  content_type: 'policy',
  source_url: 'https://example.com/returns',
  chunks_count: 3,
  created_at: '2024-01-10T00:00:00Z',
  updated_at: '2024-01-10T00:00:00Z',
};

export const mockKnowledgeArticleDetail: KnowledgeArticleDetail = {
  ...mockKnowledgeArticle,
  chunks: [
    {
      id: 'chunk-1',
      chunk_index: 0,
      content: 'Items can be returned within 30 days.',
      token_count: 8,
      has_embedding: true,
    },
  ],
};

export const mockKnowledgeArticles: KnowledgeArticle[] = [
  mockKnowledgeArticle,
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

export const mockWidgetSettings: WidgetSettings = {
  primary_color: '#0d9488',
  welcome_message: 'Hi! How can I help you today?',
  position: 'bottom-right',
  agent_name: 'Reva Support',
};

export const mockStoreSettings: StoreSettings = {
  widget: mockWidgetSettings,
};

export const mockIngestionResponse: IngestionResponse = {
  article_id: 'article-1',
  title: 'Return Policy',
  chunks_count: 3,
  status: 'completed',
  message: 'Article processed successfully',
};

export const mockProducts: Product[] = [
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
    images: [{ src: 'https://cdn.example.com/widget.jpg', alt: 'Widget photo', position: 1 }],
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

export const mockShopifyConnection: ShopifyConnection = {
  platform: 'shopify',
  platform_domain: 'test-store.myshopify.com',
  status: 'active',
  last_synced_at: '2024-01-15T10:00:00Z',
  product_count: 42,
  sync_error: null,
};

export const mockShopifyDisconnected: ShopifyConnection = {
  platform: 'shopify',
  platform_domain: '',
  status: 'disconnected',
  last_synced_at: null,
  product_count: 0,
  sync_error: null,
};

export const mockSyncStatus: SyncStatus = {
  status: 'completed',
  message: 'Sync completed successfully',
};

export function mockPaginatedResponse<T>(items: T[], page = 1, pageSize = 20): PaginatedResponse<T> {
  return {
    items,
    total: items.length,
    page,
    page_size: pageSize,
    pages: Math.ceil(items.length / pageSize) || 1,
  };
}

// === WISMO Analytics ===

export const mockWismoSummary: WismoSummary = {
  total_inquiries: 42,
  resolution_rate: 0.85,
  avg_per_day: 1.4,
  period_days: 30,
};

export const mockWismoTrend: DailyCount[] = [
  { date: '2024-01-13', count: 2 },
  { date: '2024-01-14', count: 5 },
  { date: '2024-01-15', count: 3 },
];

export const mockWismoInquiries: OrderInquiry[] = [
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
