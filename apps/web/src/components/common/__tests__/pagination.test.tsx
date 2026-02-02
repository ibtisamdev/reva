import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Pagination } from '../pagination';

describe('Pagination', () => {
  it('should not render when totalPages is 1', () => {
    const { container } = render(
      <Pagination currentPage={1} totalPages={1} onPageChange={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('should not render when totalPages is 0', () => {
    const { container } = render(
      <Pagination currentPage={1} totalPages={0} onPageChange={vi.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('should disable previous button on first page', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={vi.fn()} />);
    const nav = screen.getByRole('navigation');
    const buttons = nav.querySelectorAll('button');
    // First button is "Previous"
    expect(buttons[0]).toBeDisabled();
  });

  it('should disable next button on last page', () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={vi.fn()} />);
    const nav = screen.getByRole('navigation');
    const buttons = nav.querySelectorAll('button');
    // Last button is "Next"
    expect(buttons[buttons.length - 1]).toBeDisabled();
  });

  it('should call onPageChange when clicking a page number', async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<Pagination currentPage={1} totalPages={5} onPageChange={onPageChange} />);

    await user.click(screen.getByRole('button', { name: '2' }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('should call onPageChange with previous page when clicking previous', async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<Pagination currentPage={3} totalPages={5} onPageChange={onPageChange} />);

    const nav = screen.getByRole('navigation');
    const buttons = nav.querySelectorAll('button');
    await user.click(buttons[0]); // Previous button
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it('should call onPageChange with next page when clicking next', async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    render(<Pagination currentPage={3} totalPages={5} onPageChange={onPageChange} />);

    const nav = screen.getByRole('navigation');
    const buttons = nav.querySelectorAll('button');
    await user.click(buttons[buttons.length - 1]); // Next button
    expect(onPageChange).toHaveBeenCalledWith(4);
  });

  it('should show ellipsis for large page counts', () => {
    render(<Pagination currentPage={10} totalPages={20} onPageChange={vi.fn()} />);
    // Page 10 in the middle of 20 pages should show ellipsis on both sides
    const nav = screen.getByRole('navigation');
    // MoreHorizontal icons represent ellipsis
    const ellipses = nav.querySelectorAll('svg.lucide-ellipsis');
    expect(ellipses.length).toBe(2);
  });

  it('should always show first and last page', () => {
    render(<Pagination currentPage={10} totalPages={20} onPageChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '20' })).toBeInTheDocument();
  });
});
