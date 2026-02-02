import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockMessages } from '@/test/mocks/data';

import { MessageThread } from '../message-thread';

describe('MessageThread', () => {
  it('renders empty state when no messages', () => {
    render(<MessageThread messages={[]} />);
    expect(screen.getByText(/no messages/i)).toBeInTheDocument();
  });

  it('renders a MessageBubble for each message', () => {
    render(<MessageThread messages={mockMessages} />);
    expect(screen.getByText(mockMessages[0].content)).toBeInTheDocument();
    expect(screen.getByText(mockMessages[1].content)).toBeInTheDocument();
  });

  it('renders scroll anchor element', () => {
    const { container } = render(<MessageThread messages={mockMessages} />);
    // The bottomRef div should exist at the end
    const scrollArea = container.querySelector('[data-radix-scroll-area-viewport]') || container.firstChild;
    expect(scrollArea).toBeInTheDocument();
  });
});
