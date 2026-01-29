/**
 * Store API functions - CRUD and Settings
 */

import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from './client';
import type {
  CreateStoreRequest,
  Store,
  StoreListResponse,
  StoreSettings,
  UpdateStoreRequest,
  UpdateStoreSettingsRequest,
} from './types';

// Default widget settings
export const defaultWidgetSettings: StoreSettings = {
  widget: {
    primary_color: '#0d9488',
    welcome_message: 'Hi! How can I help you today?',
    position: 'bottom-right',
    agent_name: 'Reva Support',
  },
};

// === Store CRUD Functions ===

export async function getStores(): Promise<StoreListResponse> {
  return apiGet<StoreListResponse>('/api/v1/stores');
}

export async function getStore(storeId: string): Promise<Store> {
  return apiGet<Store>(`/api/v1/stores/${storeId}`);
}

export async function createStore(data: CreateStoreRequest): Promise<Store> {
  return apiPost<Store>('/api/v1/stores', { body: data });
}

export async function updateStore(
  storeId: string,
  data: UpdateStoreRequest
): Promise<Store> {
  return apiPatch<Store>(`/api/v1/stores/${storeId}`, { body: data });
}

export async function deleteStore(storeId: string): Promise<void> {
  return apiDelete(`/api/v1/stores/${storeId}`);
}

// === Store Settings Functions ===

export async function getStoreSettings(storeId: string): Promise<StoreSettings> {
  try {
    return await apiGet<StoreSettings>('/api/v1/stores/settings', {
      params: { store_id: storeId },
    });
  } catch (error) {
    // Return defaults only if store/settings don't exist yet (404)
    if (error instanceof ApiError && error.status === 404) {
      return defaultWidgetSettings;
    }
    // Re-throw other errors (network, server, auth, etc.)
    throw error;
  }
}

export async function updateStoreSettings(
  storeId: string,
  data: UpdateStoreSettingsRequest
): Promise<StoreSettings> {
  return apiPatch<StoreSettings>('/api/v1/stores/settings', {
    params: { store_id: storeId },
    body: data,
  });
}

// === Query Keys ===

export const storeKeys = {
  all: ['stores'] as const,
  list: () => [...storeKeys.all, 'list'] as const,
  detail: (storeId: string) => [...storeKeys.all, 'detail', storeId] as const,
  settings: (storeId: string) => [...storeKeys.all, 'settings', storeId] as const,
};
