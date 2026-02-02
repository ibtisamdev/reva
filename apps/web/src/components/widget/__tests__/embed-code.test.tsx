import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EmbedCode } from '../embed-code';

// Mock clipboard API
const mockWriteText = vi.fn().mockResolvedValue(undefined);
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: mockWriteText },
  writable: true,
  configurable: true,
});

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

describe('EmbedCode', () => {
  it('renders embed code containing the storeId', () => {
    render(<EmbedCode storeId="store-123" />);
    expect(screen.getByText(/store-123/)).toBeInTheDocument();
  });

  it('renders embed code title', () => {
    render(<EmbedCode storeId="store-123" />);
    expect(screen.getByText('Embed Code')).toBeInTheDocument();
  });

  it('copies code and shows "Copied" after clicking copy', async () => {
    const user = userEvent.setup();
    render(<EmbedCode storeId="store-123" />);

    await user.click(screen.getByRole('button', { name: /copy/i }));
    expect(screen.getByText(/copied/i)).toBeInTheDocument();
  });
});
