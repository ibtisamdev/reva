/**
 * Shopify Integration API functions
 */

import { apiGet, apiPost } from './client';
import type { ShopifyConnection, SyncStatus } from './types';

// === Query Functions ===

export async function getShopifyStatus(storeId: string): Promise<ShopifyConnection> {
  return apiGet<ShopifyConnection>('/api/v1/shopify/status', {
    params: { store_id: storeId },
  });
}

// === Mutation Functions ===

export async function disconnectShopify(storeId: string): Promise<SyncStatus> {
  return apiPost<SyncStatus>('/api/v1/shopify/disconnect', {
    params: { store_id: storeId },
  });
}

export async function triggerShopifySync(storeId: string): Promise<SyncStatus> {
  return apiPost<SyncStatus>('/api/v1/shopify/sync', {
    params: { store_id: storeId },
  });
}

// === Helpers ===

export async function getShopifyInstallUrl(storeId: string, shop: string): Promise<string> {
  const data = await apiGet<{ install_url: string }>('/api/v1/shopify/install-url', {
    params: { store_id: storeId, shop },
  });
  return data.install_url;
}

// === Query Keys ===

export const shopifyKeys = {
  all: ['shopify'] as const,
  status: (storeId: string) => [...shopifyKeys.all, 'status', storeId] as const,
};
