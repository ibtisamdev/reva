/**
 * Products API functions
 */

import { apiGet } from './client';
import type { PaginatedResponse, Product } from './types';

// === Query Functions ===

export async function getProducts(
  storeId: string,
  options?: {
    page?: number;
    pageSize?: number;
  }
): Promise<PaginatedResponse<Product>> {
  return apiGet<PaginatedResponse<Product>>('/api/v1/products', {
    params: {
      store_id: storeId,
      page: options?.page || 1,
      page_size: options?.pageSize || 20,
    },
  });
}

// === Query Keys ===

export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (storeId: string, page?: number) =>
    [...productKeys.lists(), storeId, page] as const,
};
