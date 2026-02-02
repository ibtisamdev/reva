import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import { useState, type ReactElement, type ReactNode } from 'react';

import { StoreProvider } from '@/lib/store-context';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

function AllProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => createTestQueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <StoreProvider>{children}</StoreProvider>
    </QueryClientProvider>
  );
}

function customRender(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything from testing-library, override render
export * from '@testing-library/react';
export { customRender as render };
