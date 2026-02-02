import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockConversationDetail } from '@/test/mocks/data';

import { CustomerSidebar } from '../customer-sidebar';

describe('CustomerSidebar', () => {
  it('renders customer name', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
  });

  it('renders customer email', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    expect(screen.getByText('customer@example.com')).toBeInTheDocument();
  });

  it('renders formatted first seen date', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    expect(screen.getByText(/First seen: Jan 15, 2024/)).toBeInTheDocument();
  });

  it('renders message count', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    // mockConversationDetail has 3 messages
    expect(screen.getByText(/3 messages/i)).toBeInTheDocument();
  });

  it('renders status badge', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    expect(screen.getByText(/active/i)).toBeInTheDocument();
  });

  it('renders channel label', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    expect(screen.getByText(/widget/i)).toBeInTheDocument();
  });

  it('renders session ID', () => {
    render(<CustomerSidebar conversation={mockConversationDetail} />);
    expect(screen.getByText(mockConversationDetail.session_id)).toBeInTheDocument();
  });
});
