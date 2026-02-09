import { QueryClient } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// We need to mock isServer before importing getQueryClient
// The module uses isServer from @tanstack/react-query

describe('getQueryClient', () => {
  beforeEach(() => {
    // Reset modules before each test to ensure fresh imports
    vi.resetModules();
  });

  describe('browser mode (isServer = false)', () => {
    beforeEach(() => {
      // Mock isServer as false (browser)
      vi.doMock('@tanstack/react-query', async () => {
        const actual =
          await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
        return {
          ...actual,
          isServer: false,
        };
      });
    });

    it('creates QueryClient with correct staleTime', async () => {
      const { getQueryClient } = await import('../get-query-client');
      const client = getQueryClient();

      expect(client).toBeInstanceOf(QueryClient);
      const options = client.getDefaultOptions();
      expect(options.queries?.staleTime).toBe(60 * 1000);
    });

    it('returns singleton instance on subsequent calls', async () => {
      const { getQueryClient } = await import('../get-query-client');

      const client1 = getQueryClient();
      const client2 = getQueryClient();

      expect(client1).toBe(client2);
    });

    it('maintains same cache across calls', async () => {
      const { getQueryClient } = await import('../get-query-client');

      const client1 = getQueryClient();
      // Set some cache data
      client1.setQueryData(['test-key'], { data: 'test-value' });

      const client2 = getQueryClient();
      const cachedData = client2.getQueryData(['test-key']);

      expect(cachedData).toEqual({ data: 'test-value' });
    });
  });

  describe('server mode (isServer = true)', () => {
    beforeEach(() => {
      // Mock isServer as true (server)
      vi.doMock('@tanstack/react-query', async () => {
        const actual =
          await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
        return {
          ...actual,
          isServer: true,
        };
      });
    });

    it('creates fresh client on each call', async () => {
      const { getQueryClient } = await import('../get-query-client');

      const client1 = getQueryClient();
      const client2 = getQueryClient();

      // In server mode, each call should create a new instance
      expect(client1).not.toBe(client2);
    });

    it('creates QueryClient with correct staleTime', async () => {
      const { getQueryClient } = await import('../get-query-client');
      const client = getQueryClient();

      expect(client).toBeInstanceOf(QueryClient);
      const options = client.getDefaultOptions();
      expect(options.queries?.staleTime).toBe(60 * 1000);
    });

    it('does not share cache between instances', async () => {
      const { getQueryClient } = await import('../get-query-client');

      const client1 = getQueryClient();
      client1.setQueryData(['test-key'], { data: 'server-data' });

      const client2 = getQueryClient();
      const cachedData = client2.getQueryData(['test-key']);

      // Server instances don't share cache
      expect(cachedData).toBeUndefined();
    });
  });

  describe('dehydration behavior', () => {
    beforeEach(() => {
      vi.doMock('@tanstack/react-query', async () => {
        const actual =
          await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
        return {
          ...actual,
          isServer: false,
        };
      });
    });

    it('includes pending queries in dehydration', async () => {
      const { getQueryClient } = await import('../get-query-client');
      const client = getQueryClient();

      const options = client.getDefaultOptions();
      const shouldDehydrate = options.dehydrate?.shouldDehydrateQuery;

      expect(shouldDehydrate).toBeDefined();

      // Test that pending queries are included
      // Create a mock query with pending status
      const pendingQuery = {
        state: { status: 'pending' },
        queryHash: 'test-hash',
        queryKey: ['test'],
        gcTime: 0,
      };

      // The function should return true for pending queries
      // @ts-expect-error - partial query object for testing
      const result = shouldDehydrate?.(pendingQuery);
      expect(result).toBe(true);
    });

    it('includes success queries via default behavior', async () => {
      const { getQueryClient } = await import('../get-query-client');
      const client = getQueryClient();

      const options = client.getDefaultOptions();
      const shouldDehydrate = options.dehydrate?.shouldDehydrateQuery;

      // Test that success queries are included (via defaultShouldDehydrateQuery)
      const successQuery = {
        state: { status: 'success' },
        queryHash: 'test-hash',
        queryKey: ['test'],
        gcTime: 5 * 60 * 1000, // Default gcTime
      };

      // @ts-expect-error - partial query object for testing
      const result = shouldDehydrate?.(successQuery);
      expect(result).toBe(true);
    });
  });
});
