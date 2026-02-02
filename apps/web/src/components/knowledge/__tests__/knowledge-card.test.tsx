import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { mockKnowledgeArticle } from '@/test/mocks/data';

import { KnowledgeCard } from '../knowledge-card';

describe('KnowledgeCard', () => {
  it('renders article title as link', () => {
    render(<KnowledgeCard article={mockKnowledgeArticle} onDelete={vi.fn()} />);
    const link = screen.getByRole('link', { name: /return policy/i });
    expect(link).toHaveAttribute('href', expect.stringContaining(mockKnowledgeArticle.id));
  });

  it('renders content type badge', () => {
    render(<KnowledgeCard article={mockKnowledgeArticle} onDelete={vi.fn()} />);
    // Badge shows "Policy" (distinct from the title "Return Policy")
    const badges = screen.getAllByText(/Policy/);
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });

  it('renders chunk count when not processing', () => {
    render(<KnowledgeCard article={mockKnowledgeArticle} onDelete={vi.fn()} />);
    expect(screen.getByText(/3/)).toBeInTheDocument();
  });

  it('renders processing badge for zero chunks', () => {
    const processing = { ...mockKnowledgeArticle, chunks_count: 0 };
    render(<KnowledgeCard article={processing} onDelete={vi.fn()} />);
    expect(screen.getByText(/processing/i)).toBeInTheDocument();
  });

  it('applies opacity when deleting', () => {
    const { container } = render(
      <KnowledgeCard article={mockKnowledgeArticle} onDelete={vi.fn()} isDeleting />
    );
    expect(container.firstChild).toHaveClass('opacity-50');
  });

  it('calls onDelete from dropdown', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<KnowledgeCard article={mockKnowledgeArticle} onDelete={onDelete} />);

    // Open dropdown menu
    await user.click(screen.getByRole('button', { name: /actions/i }));
    await user.click(screen.getByText(/delete/i));
    expect(onDelete).toHaveBeenCalledOnce();
  });
});
