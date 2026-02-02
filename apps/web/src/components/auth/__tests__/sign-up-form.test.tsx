import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockSignUpEmail = vi.fn();
const mockSignInSocial = vi.fn();
const mockOrgCreate = vi.fn();
const mockOrgSetActive = vi.fn();
const mockPush = vi.fn();
const mockRefresh = vi.fn();

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
  signUp: {
    email: (...args: unknown[]) => mockSignUpEmail(...args),
  },
  signIn: {
    social: (...args: unknown[]) => mockSignInSocial(...args),
  },
  organization: {
    create: (...args: unknown[]) => mockOrgCreate(...args),
    setActive: (...args: unknown[]) => mockOrgSetActive(...args),
  },
}));

import { SignUpForm } from '../sign-up-form';

describe('SignUpForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders name, email, and password fields', () => {
    render(<SignUpForm />);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders Google sign up button', () => {
    render(<SignUpForm />);
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
  });

  it('renders link to sign in', () => {
    render(<SignUpForm />);
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/sign-in');
  });

  it('submits form and creates org then redirects', async () => {
    const user = userEvent.setup();
    mockSignUpEmail.mockResolvedValue({ data: { user: { id: '1' } }, error: null });
    mockOrgCreate.mockResolvedValue({ data: { id: 'org-1' }, error: null });
    mockOrgSetActive.mockResolvedValue({});

    render(<SignUpForm />);

    await user.type(screen.getByLabelText(/name/i), 'John');
    await user.type(screen.getByLabelText(/email/i), 'john@test.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockSignUpEmail).toHaveBeenCalledWith({
        name: 'John',
        email: 'john@test.com',
        password: 'password123',
      });
    });

    expect(mockOrgCreate).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith('/dashboard');
  });

  it('displays error on failed sign up', async () => {
    const user = userEvent.setup();
    mockSignUpEmail.mockResolvedValue({
      data: null,
      error: { message: 'Email already exists' },
    });

    render(<SignUpForm />);

    await user.type(screen.getByLabelText(/name/i), 'John');
    await user.type(screen.getByLabelText(/email/i), 'john@test.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Email already exists')).toBeInTheDocument();
    });

    expect(mockPush).not.toHaveBeenCalled();
  });

  it('displays generic error on exception', async () => {
    const user = userEvent.setup();
    mockSignUpEmail.mockRejectedValue(new Error('Network error'));

    render(<SignUpForm />);

    await user.type(screen.getByLabelText(/name/i), 'John');
    await user.type(screen.getByLabelText(/email/i), 'john@test.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
    });
  });

  it('disables inputs while loading', async () => {
    const user = userEvent.setup();
    mockSignUpEmail.mockReturnValue(new Promise(() => {}));

    render(<SignUpForm />);

    await user.type(screen.getByLabelText(/name/i), 'John');
    await user.type(screen.getByLabelText(/email/i), 'john@test.com');
    await user.type(screen.getByLabelText(/password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/name/i)).toBeDisabled();
      expect(screen.getByLabelText(/email/i)).toBeDisabled();
      expect(screen.getByLabelText(/password/i)).toBeDisabled();
    });
  });
});
