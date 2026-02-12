/**
 * WISMO Analytics API functions
 */

import { apiGet } from './client';
import type {
  DailyCount,
  OrderInquiry,
  PaginatedResponse,
  WismoSummary,
} from './types';

// === Query Functions ===

export async function getWismoSummary(
  storeId: string,
  days?: number
): Promise<WismoSummary> {
  return apiGet<WismoSummary>('/api/v1/analytics/wismo/summary', {
    params: { store_id: storeId, ...(days ? { days: String(days) } : {}) },
  });
}

export async function getWismoTrend(
  storeId: string,
  days?: number
): Promise<DailyCount[]> {
  return apiGet<DailyCount[]>('/api/v1/analytics/wismo/trend', {
    params: { store_id: storeId, ...(days ? { days: String(days) } : {}) },
  });
}

export async function getWismoInquiries(
  storeId: string,
  options?: { page?: number; pageSize?: number }
): Promise<PaginatedResponse<OrderInquiry>> {
  return apiGet<PaginatedResponse<OrderInquiry>>(
    '/api/v1/analytics/wismo/inquiries',
    {
      params: {
        store_id: storeId,
        ...(options?.page ? { page: String(options.page) } : {}),
        ...(options?.pageSize
          ? { page_size: String(options.pageSize) }
          : {}),
      },
    }
  );
}

// === Query Keys ===

export const analyticsKeys = {
  all: ['analytics'] as const,
  wismo: () => [...analyticsKeys.all, 'wismo'] as const,
  wismoSummary: (storeId: string, days?: number) =>
    [...analyticsKeys.wismo(), 'summary', storeId, days] as const,
  wismoTrend: (storeId: string, days?: number) =>
    [...analyticsKeys.wismo(), 'trend', storeId, days] as const,
  wismoInquiries: (storeId: string, page?: number) =>
    [...analyticsKeys.wismo(), 'inquiries', storeId, page] as const,
};
