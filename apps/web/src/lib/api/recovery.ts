/**
 * Cart Recovery API functions
 */

import { apiGet, apiPatch, apiPost } from './client';
import type { PaginatedResponse } from './types';

// === Types ===

export interface RecoverySummary {
  total_abandoned: number;
  total_recovered: number;
  recovery_rate: number;
  recovered_revenue: number;
  emails_sent: number;
  active_sequences: number;
  period_days: number;
}

export interface RecoveryDailyCount {
  date: string;
  abandoned: number;
  recovered: number;
}

export interface RecoverySequence {
  id: string;
  abandoned_checkout_id: string;
  customer_email: string;
  sequence_type: string;
  status: string;
  current_step_index: number;
  steps_completed: Record<string, unknown>[];
  total_steps: number;
  next_step_at: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

export interface AbandonedCheckout {
  id: string;
  shopify_checkout_id: string;
  customer_email: string | null;
  customer_name: string | null;
  total_price: number;
  currency: string;
  line_items: Record<string, unknown>[];
  checkout_url: string | null;
  status: string;
  abandonment_detected_at: string | null;
  recovered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecoverySettings {
  enabled: boolean;
  min_cart_value: number;
  abandonment_threshold_minutes: number;
  sequence_timing_minutes: number[];
  discount_enabled: boolean;
  discount_percent: number;
  max_emails_per_day: number;
  exclude_email_patterns: string[];
}

// === Query Functions ===

export async function getRecoverySummary(
  storeId: string,
  days?: number
): Promise<RecoverySummary> {
  return apiGet<RecoverySummary>('/api/v1/recovery/analytics/summary', {
    params: { store_id: storeId, ...(days ? { days: String(days) } : {}) },
  });
}

export async function getRecoveryTrend(
  storeId: string,
  days?: number
): Promise<RecoveryDailyCount[]> {
  return apiGet<RecoveryDailyCount[]>('/api/v1/recovery/analytics/trend', {
    params: { store_id: storeId, ...(days ? { days: String(days) } : {}) },
  });
}

export async function getRecoverySequences(
  storeId: string,
  options?: { page?: number; pageSize?: number }
): Promise<PaginatedResponse<RecoverySequence>> {
  return apiGet<PaginatedResponse<RecoverySequence>>(
    '/api/v1/recovery/sequences',
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

export async function stopRecoverySequence(
  storeId: string,
  sequenceId: string
): Promise<{ status: string }> {
  return apiPost<{ status: string }>(
    `/api/v1/recovery/sequences/${sequenceId}/stop`,
    {
      params: { store_id: storeId },
    }
  );
}

export async function getAbandonedCheckouts(
  storeId: string,
  options?: { page?: number; pageSize?: number }
): Promise<PaginatedResponse<AbandonedCheckout>> {
  return apiGet<PaginatedResponse<AbandonedCheckout>>(
    '/api/v1/recovery/checkouts',
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

export async function getRecoverySettings(
  storeId: string
): Promise<RecoverySettings> {
  return apiGet<RecoverySettings>('/api/v1/recovery/settings', {
    params: { store_id: storeId },
  });
}

export async function updateRecoverySettings(
  storeId: string,
  data: RecoverySettings
): Promise<RecoverySettings> {
  return apiPatch<RecoverySettings>('/api/v1/recovery/settings', {
    params: { store_id: storeId },
    body: data,
  });
}

// === Query Keys ===

export const recoveryKeys = {
  all: ['recovery'] as const,
  summary: (storeId: string, days?: number) =>
    [...recoveryKeys.all, 'summary', storeId, days] as const,
  trend: (storeId: string, days?: number) =>
    [...recoveryKeys.all, 'trend', storeId, days] as const,
  sequences: (storeId: string, page?: number) =>
    [...recoveryKeys.all, 'sequences', storeId, page] as const,
  checkouts: (storeId: string, page?: number) =>
    [...recoveryKeys.all, 'checkouts', storeId, page] as const,
  settings: (storeId: string) =>
    [...recoveryKeys.all, 'settings', storeId] as const,
};
