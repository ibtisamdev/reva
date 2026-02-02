import { render, screen } from '@/test/utils';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { mockStores } from '@/test/mocks/data';

const mockSelectStore = vi.fn();
const mockRefreshStores = vi.fn();
let mockStoreState: Record<string, unknown>;

vi.mock('@/lib/store-context', () => ({
  useStore: () => mockStoreState,
  StoreProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { StoreSelector } from '../store-selector';

describe('StoreSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStoreState = {
      stores: mockStores,
      selectedStore: mockStores[0],
      isLoading: false,
      selectStore: mockSelectStore,
      refreshStores: mockRefreshStores,
    };
  });

  it('shows skeleton when loading', () => {
    mockStoreState = { ...mockStoreState, isLoading: true };
    const { container } = render(<StoreSelector />);
    expect(container.querySelector('[class*="animate-pulse"]')).toBeInTheDocument();
  });

  it('returns null when no stores', () => {
    mockStoreState = { ...mockStoreState, stores: [] };
    const { container } = render(<StoreSelector />);
    expect(container.innerHTML).toBe('');
  });

  it('renders selected store name', () => {
    render(<StoreSelector />);
    expect(screen.getByText('Test Store')).toBeInTheDocument();
  });
});
