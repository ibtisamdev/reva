import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

// Mock auth-client before importing component
const mockSignInEmail = vi.fn();
const mockSignInSocial = vi.fn();
const mockPush = vi.fn();
const mockRefresh = vi.fn();
const mockOrgList = vi.fn();
const mockSetActive = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    refresh: mockRefresh,
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/auth-client', () => ({
  signIn: {
    email: (...args: unknown[]) => mockSignInEmail(...args),
    social: (...args: unknown[]) => mockSignInSocial(...args),
  },
  organization: {
    list: (...args: unknown[]) => mockOrgList(...args),
    setActive: (...args: unknown[]) => mockSetActive(...args),
  },
}));

import { SignInForm } from '../sign-in-form';

describe('SignInForm', () => {
  it('should render email and password fields', () => {
    render(<SignInForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('should render Google sign in button', () => {
    render(<SignInForm />);
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
  });

  it('should render link to sign up', () => {
    render(<SignInForm />);
    expect(screen.getByRole('link', { name: /sign up/i })).toHaveAttribute('href', '/sign-up');
  });

  it('should submit form with email and password', async () => {
    const user = userEvent.setup();
    mockSignInEmail.mockResolvedValue({ data: { user: { id: '1' } }, error: null });
    mockOrgList.mockResolvedValue({ data: [{ id: 'org-1' }] });
    mockSetActive.mockResolvedValue({});

    render(<SignInForm />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockSignInEmail).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(mockPush).toHaveBeenCalledWith('/dashboard');
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it('should display error on failed sign in', async () => {
    const user = userEvent.setup();
    mockSignInEmail.mockResolvedValue({
      data: null,
      error: { message: 'Invalid credentials' },
    });

    render(<SignInForm />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });

    expect(mockPush).not.toHaveBeenCalled();
  });

  it('should display generic error on exception', async () => {
    const user = userEvent.setup();
    mockSignInEmail.mockRejectedValue(new Error('Network error'));

    render(<SignInForm />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
    });
  });

  it('should disable inputs while loading', async () => {
    const user = userEvent.setup();
    // Never resolve to keep loading state
    mockSignInEmail.mockReturnValue(new Promise(() => {}));

    render(<SignInForm />);

    await user.type(screen.getByLabelText(/email/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/email/i)).toBeDisabled();
      expect(screen.getByLabelText(/password/i)).toBeDisabled();
    });
  });
});
