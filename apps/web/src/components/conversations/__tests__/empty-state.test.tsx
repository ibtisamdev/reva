import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ConversationsEmptyState } from '../empty-state';

describe('ConversationsEmptyState', () => {
  it('shows "No conversations yet" when hasFilters is false', () => {
    render(<ConversationsEmptyState />);
    expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument();
  });

  it('shows "No conversations found" when hasFilters is true', () => {
    render(<ConversationsEmptyState hasFilters />);
    expect(screen.getByText(/no conversations found/i)).toBeInTheDocument();
  });

  it('shows filter hint when hasFilters is true', () => {
    render(<ConversationsEmptyState hasFilters />);
    expect(screen.getByText(/adjust/i)).toBeInTheDocument();
  });

  it('shows onboarding hint when hasFilters is false', () => {
    render(<ConversationsEmptyState />);
    expect(screen.getByText(/will appear here/i)).toBeInTheDocument();
  });
});
