import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EmptyState } from '../empty-state';

describe('EmptyState (knowledge)', () => {
  it('renders heading', () => {
    render(<EmptyState onAddClick={vi.fn()} />);
    expect(screen.getByText(/no knowledge articles yet/i)).toBeInTheDocument();
  });

  it('renders add button and calls onAddClick', async () => {
    const user = userEvent.setup();
    const onAddClick = vi.fn();
    render(<EmptyState onAddClick={onAddClick} />);

    await user.click(screen.getByRole('button', { name: /add your first article/i }));
    expect(onAddClick).toHaveBeenCalledOnce();
  });
});
