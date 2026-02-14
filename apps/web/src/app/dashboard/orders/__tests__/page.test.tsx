import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

import { render } from '@/test/utils';
import { server } from '@/test/mocks/server';
import {
  mockWismoSummary,
  mockWismoTrend,
  mockWismoInquiries,
  mockPaginatedResponse,
} from '@/test/mocks/data';

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

vi.mock('@/lib/store-context', () => ({
  useStore: () => ({
    stores: [{ id: 'store-1', name: 'Test Store' }],
    selectedStore: { id: 'store-1', name: 'Test Store' },
    selectedStoreId: 'store-1',
    isLoading: false,
    hasStores: true,
    selectStore: vi.fn(),
    refreshStores: vi.fn(),
  }),
  useRequiredStoreId: () => 'store-1',
  StoreProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import OrderInquiriesPage from '../page';

describe('OrderInquiriesPage', () => {
  it('renders page title', async () => {
    render(<OrderInquiriesPage />);

    expect(screen.getByText('Order Inquiries')).toBeInTheDocument();
  });

  it('renders page description', async () => {
    render(<OrderInquiriesPage />);

    expect(screen.getByText(/WISMO analytics/)).toBeInTheDocument();
  });

  it('renders 4 summary card titles', async () => {
    render(<OrderInquiriesPage />);

    expect(screen.getByText('Total Inquiries')).toBeInTheDocument();
    expect(screen.getByText('Resolution Rate')).toBeInTheDocument();
    expect(screen.getByText('Avg Per Day')).toBeInTheDocument();
    expect(screen.getByText('Period')).toBeInTheDocument();
  });

  it('shows loading skeletons initially', async () => {
    // Delay the response to catch loading state
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/summary`, async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json(mockWismoSummary);
      })
    );

    const { container } = render(<OrderInquiriesPage />);

    // Skeleton elements should be present during loading
    const skeletons = container.querySelectorAll('[class*="skeleton" i], [class*="animate-pulse" i]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('displays summary data after loading', async () => {
    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('1.4')).toBeInTheDocument();
    expect(screen.getByText('30 days')).toBeInTheDocument();
  });

  it('displays trend chart when data available', async () => {
    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText('Daily Trend (Last 30 Days)')).toBeInTheDocument();
    });
  });

  it('displays inquiry table with rows', async () => {
    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText('Recent Inquiries')).toBeInTheDocument();
    });

    // Table headers
    await waitFor(() => {
      expect(screen.getByText('Order #')).toBeInTheDocument();
    });
    expect(screen.getByText('Email')).toBeInTheDocument();

    // Table data from mockWismoInquiries
    await waitFor(() => {
      expect(screen.getByText('#1001')).toBeInTheDocument();
    });
    expect(screen.getByText('customer@example.com')).toBeInTheDocument();
  });

  it('shows empty state when no inquiries', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, () => {
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 1 });
      })
    );

    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText(/no order inquiries yet/i)).toBeInTheDocument();
    });
  });

  it('shows pagination controls when multiple pages', async () => {
    const manyInquiries = Array.from({ length: 25 }, (_, i) => ({
      id: `inq-${i}`,
      customer_email: `user${i}@example.com`,
      order_number: `#${1000 + i}`,
      inquiry_type: 'order_status' as const,
      order_status: 'paid',
      fulfillment_status: null,
      resolution: 'answered' as const,
      created_at: '2024-01-15T10:00:00Z',
      resolved_at: '2024-01-15T10:01:00Z',
    }));

    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, () => {
        return HttpResponse.json({
          items: manyInquiries.slice(0, 20),
          total: 25,
          page: 1,
          page_size: 20,
          pages: 2,
        });
      })
    );

    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText('Previous')).toBeInTheDocument();
    });
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument();
  });

  it('disables Previous button on first page', async () => {
    const manyInquiries = Array.from({ length: 25 }, (_, i) => ({
      id: `inq-${i}`,
      customer_email: `user${i}@example.com`,
      order_number: `#${1000 + i}`,
      inquiry_type: 'order_status' as const,
      order_status: 'paid',
      fulfillment_status: null,
      resolution: 'answered' as const,
      created_at: '2024-01-15T10:00:00Z',
      resolved_at: '2024-01-15T10:01:00Z',
    }));

    server.use(
      http.get(`${API_BASE}/api/v1/analytics/wismo/inquiries`, () => {
        return HttpResponse.json({
          items: manyInquiries.slice(0, 20),
          total: 25,
          page: 1,
          page_size: 20,
          pages: 2,
        });
      })
    );

    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText('Previous')).toBeInTheDocument();
    });

    const prevButton = screen.getByText('Previous').closest('button');
    expect(prevButton).toBeDisabled();
  });

  it('renders badges for inquiry type and resolution', async () => {
    render(<OrderInquiriesPage />);

    await waitFor(() => {
      expect(screen.getByText('order status')).toBeInTheDocument();
    });
    expect(screen.getByText('answered')).toBeInTheDocument();
    expect(screen.getByText('verification failed')).toBeInTheDocument();
  });
});
