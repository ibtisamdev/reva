import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockMessages } from '@/test/mocks/data';

import { MessageBubble } from '../message-bubble';

const [userMsg, assistantMsg, systemMsg] = mockMessages;

describe('MessageBubble', () => {
  it('renders user message content', () => {
    render(<MessageBubble message={userMsg} />);
    expect(screen.getByText(userMsg.content)).toBeInTheDocument();
  });

  it('renders assistant message content', () => {
    render(<MessageBubble message={assistantMsg} />);
    expect(screen.getByText(assistantMsg.content)).toBeInTheDocument();
  });

  it('renders system message as centered pill', () => {
    render(<MessageBubble message={systemMsg} />);
    expect(screen.getByText(systemMsg.content)).toBeInTheDocument();
  });

  it('renders timestamp', () => {
    render(<MessageBubble message={userMsg} />);
    // format "h:mm a" from date-fns
    expect(screen.getByText(/\d{1,2}:\d{2}\s?(AM|PM)/i)).toBeInTheDocument();
  });

  it('renders source citations for assistant messages', () => {
    render(<MessageBubble message={assistantMsg} />);
    expect(screen.getByText('Return Policy')).toBeInTheDocument();
    expect(screen.getByText('FAQ')).toBeInTheDocument();
  });

  it('renders external link icon for sources with URLs', () => {
    render(<MessageBubble message={assistantMsg} />);
    // The first source has a URL, should render a link
    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(links[0]).toHaveAttribute('href', 'https://example.com/returns');
  });

  it('does not render sources for user messages', () => {
    render(<MessageBubble message={userMsg} />);
    expect(screen.queryByText('Return Policy')).not.toBeInTheDocument();
  });
});
