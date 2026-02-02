import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { act, type ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { StoreProvider, useRequiredStoreId, useStore } from '../store-context';

// Mock auth-client
vi.mock('@/lib/auth-client', () => ({
  getAuthToken: vi.fn().mockResolvedValue('test-token'),
  signIn: { email: vi.fn(), social: vi.fn() },
  signUp: { email: vi.fn() },
  signOut: vi.fn(),
  useSession: vi.fn(),
  organization: {},
  authClient: {},
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <StoreProvider>{children}</StoreProvider>
    </QueryClientProvider>
  );
  Wrapper.displayName = 'TestWrapper';
  return Wrapper;
}

// localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('useStore', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('should auto-select first store when none saved', async () => {
    const { result } = renderHook(() => useStore(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.selectedStoreId).toBe('store-1');
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'reva_selected_store_id',
      'store-1'
    );
  });

  it('should restore selected store from localStorage', async () => {
    localStorageMock.setItem('reva_selected_store_id', 'store-2');

    const { result } = renderHook(() => useStore(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.selectedStoreId).toBe('store-2');
  });

  it('should expose stores list filtered to active only', async () => {
    const { result } = renderHook(() => useStore(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.stores).toHaveLength(2);
    expect(result.current.hasStores).toBe(true);
  });

  it('should switch store and persist to localStorage', async () => {
    const { result } = renderHook(() => useStore(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    act(() => {
      result.current.selectStore('store-2');
    });

    expect(result.current.selectedStoreId).toBe('store-2');
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'reva_selected_store_id',
      'store-2'
    );
  });
});

describe('useRequiredStoreId', () => {
  it('should throw when no store is selected', () => {
    // Render without stores loaded - suppress console.error from React
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useRequiredStoreId(), { wrapper: createWrapper() });
    }).toThrow('useRequiredStoreId must be used within a page where a store is guaranteed');

    spy.mockRestore();
  });
});

describe('useStore outside provider', () => {
  it('should throw when used outside StoreProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const wrapper = ({ children }: { children: ReactNode }) => {
      const queryClient = new QueryClient();
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    };

    expect(() => {
      renderHook(() => useStore(), { wrapper });
    }).toThrow('useStore must be used within a StoreProvider');

    spy.mockRestore();
  });
});
