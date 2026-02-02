import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

let mockStoreState: { isLoading: boolean; hasStores: boolean; selectedStoreId: string | null };

vi.mock('@/lib/store-context', () => ({
  useStore: () => mockStoreState,
  StoreProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/components/dashboard/no-store-state', () => ({
  NoStoreState: () => <div data-testid="no-store-state">No Store</div>,
}));

import { DashboardContent } from '../dashboard-content';

describe('DashboardContent', () => {
  it('shows loading spinner when isLoading', () => {
    mockStoreState = { isLoading: true, hasStores: false, selectedStoreId: null };
    const { container } = render(<DashboardContent>child</DashboardContent>);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('shows NoStoreState when no stores', () => {
    mockStoreState = { isLoading: false, hasStores: false, selectedStoreId: null };
    render(<DashboardContent>child</DashboardContent>);
    expect(screen.getByTestId('no-store-state')).toBeInTheDocument();
  });

  it('shows NoStoreState when no selected store', () => {
    mockStoreState = { isLoading: false, hasStores: true, selectedStoreId: null };
    render(<DashboardContent>child</DashboardContent>);
    expect(screen.getByTestId('no-store-state')).toBeInTheDocument();
  });

  it('renders children when store is selected', () => {
    mockStoreState = { isLoading: false, hasStores: true, selectedStoreId: 'store-1' };
    render(<DashboardContent><div>Dashboard child content</div></DashboardContent>);
    expect(screen.getByText('Dashboard child content')).toBeInTheDocument();
  });
});
