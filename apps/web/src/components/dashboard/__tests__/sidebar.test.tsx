import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

let mockPathname = '/dashboard';

vi.mock('next/link', () => ({
  default: ({ children, href, className, ...props }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className} {...props}>{children}</a>
  ),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
}));

vi.mock('@/components/dashboard/store-selector', () => ({
  StoreSelector: () => <div data-testid="store-selector">Store Selector</div>,
}));

vi.mock('@/lib/store-context', () => ({
  useStore: () => ({ stores: [], selectedStore: null, isLoading: false, selectStore: vi.fn(), refreshStores: vi.fn() }),
  StoreProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { Sidebar } from '../sidebar';

describe('Sidebar', () => {
  it('renders logo link to dashboard', () => {
    render(<Sidebar />);
    expect(screen.getByText('Reva')).toBeInTheDocument();
  });

  it('renders 4 navigation links', () => {
    render(<Sidebar />);
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Conversations')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
    expect(screen.getByText('Widget Settings')).toBeInTheDocument();
  });

  it('highlights active nav link', () => {
    mockPathname = '/dashboard/conversations';
    render(<Sidebar />);
    const convLink = screen.getByText('Conversations').closest('a');
    expect(convLink).toHaveClass('bg-primary');
  });

  it('renders store selector', () => {
    render(<Sidebar />);
    expect(screen.getByTestId('store-selector')).toBeInTheDocument();
  });
});
