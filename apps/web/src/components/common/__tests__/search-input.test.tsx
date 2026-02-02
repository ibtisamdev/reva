import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SearchInput } from '../search-input';

describe('SearchInput', () => {
  it('should render with placeholder', () => {
    render(<SearchInput value="" onChange={vi.fn()} placeholder="Search items..." />);
    expect(screen.getByPlaceholderText('Search items...')).toBeInTheDocument();
  });

  it('should render default placeholder', () => {
    render(<SearchInput value="" onChange={vi.fn()} />);
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument();
  });

  it('should show clear button when value is present', () => {
    render(<SearchInput value="test" onChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument();
  });

  it('should not show clear button when empty', () => {
    render(<SearchInput value="" onChange={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /clear search/i })).not.toBeInTheDocument();
  });

  it('should call onChange immediately when clearing', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchInput value="test" onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: /clear search/i }));
    expect(onChange).toHaveBeenCalledWith('');
  });

  it('should debounce onChange when typing', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchInput value="" onChange={onChange} debounceMs={100} />);

    const input = screen.getByPlaceholderText('Search...');
    await user.type(input, 'hi');

    // onChange should not have been called synchronously during typing
    // but after debounce it should fire
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('hi');
    });
  });
});
