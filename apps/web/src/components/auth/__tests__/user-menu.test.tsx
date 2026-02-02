import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockPush = vi.fn();
const mockRefresh = vi.fn();
const mockSignOut = vi.fn().mockResolvedValue(undefined);
let mockSessionData: { data: unknown; isPending: boolean };

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    refresh: mockRefresh,
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/auth-client', () => ({
  useSession: () => mockSessionData,
  signOut: (...args: unknown[]) => mockSignOut(...args),
}));

import { UserMenu } from '../user-menu';

describe('UserMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSessionData = { data: null, isPending: false };
  });

  it('shows loading skeleton when session is pending', () => {
    mockSessionData = { data: null, isPending: true };
    const { container } = render(<UserMenu />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows "Sign in" button when no session', () => {
    mockSessionData = { data: null, isPending: false };
    render(<UserMenu />);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('navigates to sign-in on click', async () => {
    const user = userEvent.setup();
    mockSessionData = { data: null, isPending: false };
    render(<UserMenu />);

    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(mockPush).toHaveBeenCalledWith('/sign-in');
  });

  it('renders avatar with initials when authenticated', () => {
    mockSessionData = {
      data: { user: { name: 'Jane Doe', email: 'jane@test.com', image: null } },
      isPending: false,
    };
    render(<UserMenu />);
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('shows dropdown with user info', async () => {
    const user = userEvent.setup();
    mockSessionData = {
      data: { user: { name: 'Jane Doe', email: 'jane@test.com', image: null } },
      isPending: false,
    };
    render(<UserMenu />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('jane@test.com')).toBeInTheDocument();
  });

  it('signs out and redirects', async () => {
    const user = userEvent.setup();
    mockSessionData = {
      data: { user: { name: 'Jane Doe', email: 'jane@test.com', image: null } },
      isPending: false,
    };
    render(<UserMenu />);

    await user.click(screen.getByRole('button'));
    await user.click(screen.getByText('Sign out'));

    expect(mockSignOut).toHaveBeenCalled();
  });
});
