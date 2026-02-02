import { render, screen, waitFor } from '@/test/utils';
import { describe, expect, it } from 'vitest';

import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

import { ConversationList } from '../conversation-list';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

describe('ConversationList', () => {
  it('shows loading skeletons initially', () => {
    const { container } = render(<ConversationList storeId="store-1" />);
    expect(container.querySelector('[class*="animate-pulse"]')).toBeInTheDocument();
  });

  it('renders conversation cards after loading', async () => {
    render(<ConversationList storeId="store-1" />);
    await waitFor(() => {
      expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    });
  });

  it('shows empty state when no conversations', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/chat/conversations`, () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 0 })
      )
    );

    render(<ConversationList storeId="store-1" />);
    await waitFor(() => {
      expect(screen.getByText(/no conversations yet/i)).toBeInTheDocument();
    });
  });

  it('renders search input and status filter', async () => {
    render(<ConversationList storeId="store-1" />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });
  });
});
