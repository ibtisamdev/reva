import { render, screen } from '@/test/utils';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockSelectStore = vi.fn();
const mockRefreshStores = vi.fn();

vi.mock('@/lib/store-context', () => ({
  useStore: () => ({
    selectStore: mockSelectStore,
    refreshStores: mockRefreshStores,
    stores: [],
    selectedStore: null,
    selectedStoreId: null,
    isLoading: false,
    hasStores: false,
  }),
  StoreProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/lib/auth-client', () => ({
  useSession: () => ({ data: { user: { name: 'Test User' } }, isPending: false }),
  organization: {
    getFullOrganization: vi.fn().mockResolvedValue({ data: { id: 'org-1' } }),
    create: vi.fn().mockResolvedValue({ data: { id: 'org-1' }, error: null }),
    setActive: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { NoStoreState } from '../no-store-state';

describe('NoStoreState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders welcome heading', () => {
    render(<NoStoreState />);
    expect(screen.getByText(/welcome to reva/i)).toBeInTheDocument();
  });

  it('renders store name input', () => {
    render(<NoStoreState />);
    expect(screen.getByLabelText(/store name/i)).toBeInTheDocument();
  });

  it('disables submit when input is empty', () => {
    render(<NoStoreState />);
    expect(screen.getByRole('button', { name: /create store/i })).toBeDisabled();
  });

  it('enables submit when input has value', async () => {
    const user = userEvent.setup();
    render(<NoStoreState />);

    await user.type(screen.getByLabelText(/store name/i), 'My Store');
    expect(screen.getByRole('button', { name: /create store/i })).toBeEnabled();
  });
});
