import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import type { ShopifyConnection } from '@/lib/api/types';

const mockGetShopifyStatus = vi.fn();
const mockDisconnectShopify = vi.fn();
const mockTriggerShopifySync = vi.fn();
const mockGetShopifyInstallUrl = vi.fn();

vi.mock('@/lib/api/shopify', () => ({
  getShopifyStatus: (...args: unknown[]) => mockGetShopifyStatus(...args),
  disconnectShopify: (...args: unknown[]) => mockDisconnectShopify(...args),
  triggerShopifySync: (...args: unknown[]) => mockTriggerShopifySync(...args),
  getShopifyInstallUrl: (...args: unknown[]) => mockGetShopifyInstallUrl(...args),
  shopifyKeys: {
    all: ['shopify'] as const,
    status: (storeId: string) => ['shopify', 'status', storeId] as const,
  },
}));

vi.mock('@/lib/api/products', () => ({
  productKeys: {
    all: ['products'] as const,
  },
}));

vi.mock('@/lib/store-context', () => ({
  useRequiredStoreId: () => 'store-1',
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { ShopifyConnectCard } from '../shopify-connect-card';

const activeConnection: ShopifyConnection = {
  platform: 'shopify',
  platform_domain: 'test-store.myshopify.com',
  status: 'active',
  last_synced_at: '2024-01-15T10:00:00Z',
  product_count: 42,
};

const disconnectedConnection: ShopifyConnection = {
  platform: 'shopify',
  platform_domain: '',
  status: 'disconnected',
  last_synced_at: null,
  product_count: 0,
};

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe('ShopifyConnectCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: return disconnected
    mockGetShopifyStatus.mockResolvedValue(disconnectedConnection);
    mockDisconnectShopify.mockResolvedValue({ status: 'completed', message: 'Done' });
    mockTriggerShopifySync.mockResolvedValue({ status: 'completed', message: 'Done' });
    mockGetShopifyInstallUrl.mockResolvedValue('https://test.myshopify.com/admin/oauth/authorize');
  });

  it('shows disconnected state with input and connect button', async () => {
    renderWithQuery(<ShopifyConnectCard />);
    await waitFor(() => {
      expect(screen.getByText('Not Connected')).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/shop domain/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /connect shopify/i })).toBeInTheDocument();
  });

  it('connect button is disabled when input is empty', async () => {
    renderWithQuery(<ShopifyConnectCard />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /connect shopify/i })).toBeDisabled();
    });
  });

  it('shows connected state with store info and action buttons', async () => {
    mockGetShopifyStatus.mockResolvedValue(activeConnection);
    renderWithQuery(<ShopifyConnectCard />);
    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });
    expect(screen.getByText('test-store.myshopify.com')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /resync products/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /disconnect/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /shopify admin/i })).toHaveAttribute(
      'href',
      'https://test-store.myshopify.com/admin'
    );
  });

  it('calls triggerShopifySync when Resync is clicked', async () => {
    const user = userEvent.setup();
    mockGetShopifyStatus.mockResolvedValue(activeConnection);
    renderWithQuery(<ShopifyConnectCard />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /resync products/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /resync products/i }));
    await waitFor(() => {
      expect(mockTriggerShopifySync).toHaveBeenCalled();
    });
  });

  it('calls disconnectShopify when Disconnect is clicked', async () => {
    const user = userEvent.setup();
    mockGetShopifyStatus.mockResolvedValue(activeConnection);
    renderWithQuery(<ShopifyConnectCard />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /disconnect/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /disconnect/i }));
    await waitFor(() => {
      expect(mockDisconnectShopify).toHaveBeenCalled();
    });
  });

  it('calls getShopifyInstallUrl on connect with auto-suffixed domain', async () => {
    const user = userEvent.setup();
    vi.stubGlobal('location', { ...window.location, href: '' });

    try {
      renderWithQuery(<ShopifyConnectCard />);
      await waitFor(() => {
        expect(screen.getByLabelText(/shop domain/i)).toBeInTheDocument();
      });
      await user.type(screen.getByLabelText(/shop domain/i), 'mystore');
      await user.click(screen.getByRole('button', { name: /connect shopify/i }));

      await waitFor(() => {
        expect(mockGetShopifyInstallUrl).toHaveBeenCalledWith('store-1', 'mystore.myshopify.com');
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
