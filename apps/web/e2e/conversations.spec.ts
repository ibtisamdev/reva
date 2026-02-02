import { test, expect, mockData } from './fixtures';

test.describe('Conversations', () => {
  test('list renders conversation cards with customer info', async ({ mockApi: page }) => {
    await page.goto('/dashboard/conversations');
    await expect(page.getByText('Jane Doe')).toBeVisible();
    await expect(page.getByText(/active/i).first()).toBeVisible();
    await expect(page.getByText(/widget/i).first()).toBeVisible();
  });

  test('shows "Anonymous" for null customer name', async ({ mockApi: page }) => {
    await page.route('**/api/v1/chat/conversations**', (route) => {
      const url = new URL(route.request().url());
      // Skip detail routes like /conversations/conv-1
      if (/\/conversations\/[^/?]/.test(url.pathname)) return route.fallback();
      return route.fulfill({
        json: mockData.paginated([
          { ...mockData.MOCK_CONVERSATIONS[0], customer_name: null, customer_email: null },
        ]),
      });
    });

    await page.goto('/dashboard/conversations');
    await expect(page.getByText('Anonymous')).toBeVisible();
  });

  test('shows empty state when no conversations', async ({ mockApi: page }) => {
    await page.route('**/api/v1/chat/conversations**', (route) => {
      const url = new URL(route.request().url());
      if (/\/conversations\/[^/?]/.test(url.pathname)) return route.fallback();
      return route.fulfill({ json: mockData.paginated([]) });
    });

    await page.goto('/dashboard/conversations');
    await expect(page.getByText(/no conversations yet/i)).toBeVisible();
  });

  test('search input is present', async ({ mockApi: page }) => {
    await page.goto('/dashboard/conversations');
    await expect(page.getByPlaceholder(/search/i)).toBeVisible();
  });

  test('status filter dropdown is present', async ({ mockApi: page }) => {
    await page.goto('/dashboard/conversations');
    await expect(page.getByText('All Status')).toBeVisible();
  });

  test('clicking card navigates to conversation detail', async ({ mockApi: page }) => {
    await page.goto('/dashboard/conversations');
    await page.getByText('Jane Doe').click();
    await expect(page).toHaveURL(/\/dashboard\/conversations\/conv-1/);
  });

  test('conversation detail shows message thread and customer sidebar', async ({ mockApi: page }) => {
    await page.goto('/dashboard/conversations/conv-1');
    // Message content
    await expect(page.getByText('How do I return an item?')).toBeVisible();
    await expect(page.getByText('You can return items within 30 days of purchase.')).toBeVisible();
    // Customer sidebar
    await expect(page.getByText('Jane Doe').first()).toBeVisible();
    await expect(page.getByText('customer@example.com').first()).toBeVisible();
  });

  test('search filters conversations by customer name', async ({ mockApi: page }) => {
    const searchedConversation = {
      ...mockData.MOCK_CONVERSATIONS[0],
      id: 'conv-search',
      customer_name: 'Alice Smith',
      customer_email: 'alice@example.com',
    };

    await page.route('**/api/v1/chat/conversations**', (route) => {
      const url = new URL(route.request().url());
      const search = url.searchParams.get('search');
      if (search === 'Alice') {
        return route.fulfill({ json: mockData.paginated([searchedConversation]) });
      }
      return route.fulfill({ json: mockData.paginated(mockData.MOCK_CONVERSATIONS) });
    });

    await page.goto('/dashboard/conversations');
    await expect(page.getByText('Jane Doe')).toBeVisible();

    await page.getByPlaceholder(/search/i).fill('Alice');

    await expect(page.getByText('Alice Smith')).toBeVisible();
    await expect(page.getByText('Jane Doe')).not.toBeVisible();
  });

  test('status filter shows only matching conversations', async ({ mockApi: page }) => {
    const resolvedConversation = {
      ...mockData.MOCK_CONVERSATIONS[1],
      customer_name: 'Bob Resolved',
      status: 'resolved',
    };

    await page.route('**/api/v1/chat/conversations**', (route) => {
      const url = new URL(route.request().url());
      const status = url.searchParams.get('status');
      if (status === 'resolved') {
        return route.fulfill({ json: mockData.paginated([resolvedConversation]) });
      }
      return route.fulfill({ json: mockData.paginated(mockData.MOCK_CONVERSATIONS) });
    });

    await page.goto('/dashboard/conversations');

    // Open status filter (second combobox - first is the store selector)
    const statusFilter = page.getByText('All Status');
    await statusFilter.click();
    await page.getByRole('option', { name: 'Resolved' }).click();

    await expect(page.getByText('Bob Resolved')).toBeVisible();
  });

  test('mark resolved button updates conversation status', async ({ mockApi: page }) => {
    let patchCalled = false;
    await page.route('**/api/v1/chat/conversations/conv-1/status**', (route) => {
      patchCalled = true;
      return route.fulfill({
        json: { ...mockData.MOCK_CONVERSATION_DETAIL, status: 'resolved' },
      });
    });

    await page.goto('/dashboard/conversations/conv-1');
    const resolveButton = page.getByRole('button', { name: /mark resolved/i });
    await expect(resolveButton).toBeVisible();
    await resolveButton.click();

    await expect(page.getByText(/conversation marked as resolved/i)).toBeVisible({ timeout: 5000 });
    expect(patchCalled).toBe(true);
  });

  test('pagination controls appear for large conversation lists', async ({ mockApi: page }) => {
    // Generate 25 conversations to trigger pagination (page size = 20)
    const manyConversations = Array.from({ length: 25 }, (_, i) => ({
      ...mockData.MOCK_CONVERSATIONS[0],
      id: `conv-${i}`,
      customer_name: `Customer ${i}`,
    }));

    await page.route('**/api/v1/chat/conversations**', (route) => {
      const url = new URL(route.request().url());
      const pageNum = parseInt(url.searchParams.get('page') || '1');
      const pageSize = 20;
      const start = (pageNum - 1) * pageSize;
      const items = manyConversations.slice(start, start + pageSize);
      return route.fulfill({
        json: { items, total: 25, page: pageNum, page_size: pageSize, pages: 2 },
      });
    });

    await page.goto('/dashboard/conversations');
    // Pagination should be visible
    const pagination = page.locator('nav[aria-label="Pagination"]');
    await expect(pagination).toBeVisible();

    // Click next page
    await pagination.getByText('Next').click();
    await expect(page.getByText('Customer 20')).toBeVisible();
  });
});
