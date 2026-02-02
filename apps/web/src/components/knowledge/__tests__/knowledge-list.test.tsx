import { render, screen, waitFor } from '@/test/utils';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

import { KnowledgeList } from '../knowledge-list';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

describe('KnowledgeList', () => {
  it('shows loading spinner initially', () => {
    const { container } = render(<KnowledgeList storeId="store-1" />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders knowledge cards after loading', async () => {
    render(<KnowledgeList storeId="store-1" />);
    await waitFor(() => {
      expect(screen.getByText('Return Policy')).toBeInTheDocument();
      expect(screen.getByText('Shipping FAQ')).toBeInTheDocument();
    });
  });

  it('shows empty state when no articles', async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/knowledge`, () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, pages: 0 })
      )
    );

    render(<KnowledgeList storeId="store-1" />);
    await waitFor(() => {
      expect(screen.getByText(/no knowledge articles yet/i)).toBeInTheDocument();
    });
  });

  it('renders "Add Content" button', async () => {
    render(<KnowledgeList storeId="store-1" />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add content/i })).toBeInTheDocument();
    });
  });
});
