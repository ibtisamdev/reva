'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { getStores, storeKeys } from '@/lib/api/stores';
import type { Store } from '@/lib/api/types';

const SELECTED_STORE_KEY = 'reva_selected_store_id';

interface StoreContextValue {
  // State
  stores: Store[];
  selectedStore: Store | null;
  selectedStoreId: string | null;
  isLoading: boolean;
  hasStores: boolean;

  // Actions
  selectStore: (storeId: string) => void;
  refreshStores: () => Promise<void>;
}

const StoreContext = createContext<StoreContextValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Fetch stores for the organization
  const { data, isLoading, refetch } = useQuery({
    queryKey: storeKeys.list(),
    queryFn: getStores,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const stores = useMemo(() => {
    // Filter to only active stores
    return (data?.items ?? []).filter((store) => store.is_active);
  }, [data?.items]);

  const hasStores = stores.length > 0;

  // Initialize from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined' && !isInitialized) {
      const savedId = localStorage.getItem(SELECTED_STORE_KEY);
      if (savedId) {
        setSelectedStoreId(savedId);
      }
      setIsInitialized(true);
    }
  }, [isInitialized]);

  // Auto-select first store if none selected
  useEffect(() => {
    if (isInitialized && !isLoading && hasStores && !selectedStoreId) {
      const firstStore = stores[0];
      setSelectedStoreId(firstStore.id);
      localStorage.setItem(SELECTED_STORE_KEY, firstStore.id);
    }
  }, [isInitialized, isLoading, hasStores, stores, selectedStoreId]);

  // Validate selected store still exists
  useEffect(() => {
    if (isInitialized && !isLoading && selectedStoreId) {
      const storeExists = stores.some((s) => s.id === selectedStoreId);
      if (!storeExists && hasStores) {
        // Selected store no longer exists, select first available
        const firstStore = stores[0];
        setSelectedStoreId(firstStore.id);
        localStorage.setItem(SELECTED_STORE_KEY, firstStore.id);
      } else if (!storeExists && !hasStores) {
        // No stores at all
        setSelectedStoreId(null);
        localStorage.removeItem(SELECTED_STORE_KEY);
      }
    }
  }, [isInitialized, isLoading, selectedStoreId, stores, hasStores]);

  const selectedStore = useMemo(() => {
    if (!selectedStoreId) return null;
    return stores.find((s) => s.id === selectedStoreId) ?? null;
  }, [stores, selectedStoreId]);

  const selectStore = useCallback(
    (storeId: string) => {
      setSelectedStoreId(storeId);
      localStorage.setItem(SELECTED_STORE_KEY, storeId);

      // Invalidate store-specific queries to refetch with new store
      queryClient.invalidateQueries({ queryKey: ['knowledge'] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
    [queryClient]
  );

  const refreshStores = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const value = useMemo(
    () => ({
      stores,
      selectedStore,
      selectedStoreId,
      isLoading: isLoading || !isInitialized,
      hasStores,
      selectStore,
      refreshStores,
    }),
    [
      stores,
      selectedStore,
      selectedStoreId,
      isLoading,
      isInitialized,
      hasStores,
      selectStore,
      refreshStores,
    ]
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

/**
 * Hook to access the store context.
 * Returns stores, selected store, loading state, and store selection actions.
 */
export function useStore() {
  const context = useContext(StoreContext);
  if (!context) {
    throw new Error('useStore must be used within a StoreProvider');
  }
  return context;
}

/**
 * Hook to get the currently selected store ID.
 * Throws if no store is selected (should be used in components wrapped by store guard).
 */
export function useRequiredStoreId(): string {
  const { selectedStoreId } = useStore();
  if (!selectedStoreId) {
    throw new Error('No store selected. User should be redirected to onboarding.');
  }
  return selectedStoreId;
}

/**
 * Hook to get the currently selected store.
 * Returns the store object or null if loading/no store selected.
 */
export function useSelectedStore(): Store | null {
  const { selectedStore } = useStore();
  return selectedStore;
}
