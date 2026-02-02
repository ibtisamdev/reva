import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Conversation } from '@/lib/api/types';
import { mockConversation } from '@/test/mocks/data';

import { ConversationCard } from '../conversation-card';

describe('ConversationCard', () => {
  it('renders customer name when available', () => {
    render(<ConversationCard conversation={mockConversation} />);
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
  });

  it('renders email when name is null', () => {
    const conv: Conversation = { ...mockConversation, customer_name: null, customer_email: 'test@example.com' };
    render(<ConversationCard conversation={conv} />);
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('renders "Anonymous" when both name and email are null', () => {
    const conv: Conversation = { ...mockConversation, customer_name: null, customer_email: null };
    render(<ConversationCard conversation={conv} />);
    expect(screen.getByText('Anonymous')).toBeInTheDocument();
  });

  it('renders status badge', () => {
    render(<ConversationCard conversation={mockConversation} />);
    expect(screen.getByText(/active/i)).toBeInTheDocument();
  });

  it('renders channel label', () => {
    render(<ConversationCard conversation={mockConversation} />);
    expect(screen.getByText(/widget/i)).toBeInTheDocument();
  });

  it('links to the conversation detail page', () => {
    render(<ConversationCard conversation={mockConversation} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', expect.stringContaining(mockConversation.id));
  });

  it('renders truncated session ID', () => {
    render(<ConversationCard conversation={mockConversation} />);
    // Displays "Session: {first 8 chars}..."
    expect(screen.getByText(/sess-abc/)).toBeInTheDocument();
  });
});
