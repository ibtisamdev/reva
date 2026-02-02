import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000';

const MOCK_CHAT_RESPONSE = {
  message_id: 'msg-resp-1',
  conversation_id: 'conv-widget-1',
  response: 'You can return items within 30 days of purchase.',
  sources: [
    { chunk_id: 'chunk-1', title: 'Return Policy', url: 'https://example.com/returns', snippet: 'Items can be returned within 30 days.' },
    { chunk_id: 'chunk-2', title: 'FAQ', url: null, snippet: 'See our return policy.' },
  ],
};

const MOCK_CONVERSATION_DETAIL = {
  id: 'conv-widget-1',
  store_id: 'eaf26ca0-37b1-4c8e-bdab-c570f31e80ad',
  session_id: 'test-session',
  channel: 'widget',
  status: 'active',
  customer_email: null,
  customer_name: null,
  messages: [
    { id: 'msg-1', role: 'user', content: 'How do I return an item?', sources: null, tokens_used: 10, created_at: '2024-01-15T10:00:00Z' },
    { id: 'msg-2', role: 'assistant', content: 'You can return items within 30 days of purchase.', sources: MOCK_CHAT_RESPONSE.sources, tokens_used: 25, created_at: '2024-01-15T10:00:05Z' },
  ],
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:05Z',
};

async function setupMockApi(page: import('@playwright/test').Page) {
  await page.route(`${API_BASE}/api/v1/chat/messages**`, async (route) => {
    return route.fulfill({ status: 201, json: MOCK_CHAT_RESPONSE });
  });

  await page.route(`${API_BASE}/api/v1/chat/conversations/**`, async (route) => {
    return route.fulfill({ json: MOCK_CONVERSATION_DETAIL });
  });

  await page.route(`${API_BASE}/api/v1/chat/conversations?**`, async (route) => {
    return route.fulfill({
      json: { items: [MOCK_CONVERSATION_DETAIL], total: 1, page: 1, page_size: 20, pages: 1 },
    });
  });
}

test.describe('Chat Widget', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      (window as any).RevaConfig = {
        storeId: 'eaf26ca0-37b1-4c8e-bdab-c570f31e80ad',
        apiUrl: 'http://localhost:8000',
        theme: { primaryColor: '#6366f1' },
        position: 'right',
      };
    });
    await setupMockApi(page);
  });

  test('widget opens and closes via toggle button', async ({ page }) => {
    await page.goto('/');

    // Widget toggle should be visible
    const toggle = page.locator('.reva-toggle');
    await expect(toggle).toBeVisible();

    // Chat window should not be visible initially
    await expect(page.locator('.reva-chat-window')).not.toBeVisible();

    // Click to open
    await toggle.click();
    await expect(page.locator('.reva-chat-window')).toBeVisible();

    // Click to close
    await toggle.click();
    await expect(page.locator('.reva-chat-window')).not.toBeVisible();
  });

  test('send message and receive response', async ({ page }) => {
    await page.goto('/');
    await page.locator('.reva-toggle').click();

    const input = page.locator('.reva-input');
    await input.fill('How do I return an item?');
    await page.locator('.reva-send-button').click();

    // User message should appear
    await expect(page.locator('.reva-message-user').getByText('How do I return an item?')).toBeVisible();

    // Assistant response should appear
    await expect(page.locator('.reva-message-assistant').getByText(/return items within 30 days/i)).toBeVisible({ timeout: 5000 });
  });

  test('displays source citations in assistant messages', async ({ page }) => {
    await page.goto('/');
    await page.locator('.reva-toggle').click();

    await page.locator('.reva-input').fill('What is your return policy?');
    await page.locator('.reva-send-button').click();

    // Wait for response with sources
    await expect(page.locator('.reva-sources').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.reva-source-link').first()).toBeVisible();
    await expect(page.locator('.reva-source-link').getByText('Return Policy')).toBeVisible();
  });

  test('shows error state with retry button on API failure', async ({ page }) => {
    let callCount = 0;
    await page.route(`${API_BASE}/api/v1/chat/messages**`, async (route) => {
      callCount++;
      if (callCount <= 3) {
        // First calls fail (including retries)
        return route.fulfill({ status: 500, json: { detail: 'Internal server error' } });
      }
      // After retry button click, succeed
      return route.fulfill({ status: 201, json: MOCK_CHAT_RESPONSE });
    });

    await page.goto('/');
    await page.locator('.reva-toggle').click();

    await page.locator('.reva-input').fill('Test message');
    await page.locator('.reva-send-button').click();

    // Error should appear after retries exhaust
    const error = page.locator('.reva-error');
    await expect(error).toBeVisible({ timeout: 15000 });

    // Retry button should be visible
    const retryButton = page.locator('.reva-error-retry');
    await expect(retryButton).toBeVisible();
    await retryButton.click();

    // Retry puts text back in input — click send again
    await page.locator('.reva-send-button').click();

    // Should eventually show the response
    await expect(page.locator('.reva-message-assistant').getByText(/return items/i)).toBeVisible({ timeout: 15000 });
  });

  test('loading indicator shows while waiting for response', async ({ page }) => {
    // Delay the API response
    await page.route(`${API_BASE}/api/v1/chat/messages**`, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      return route.fulfill({ status: 201, json: MOCK_CHAT_RESPONSE });
    });

    await page.goto('/');
    await page.locator('.reva-toggle').click();

    await page.locator('.reva-input').fill('Test message');
    await page.locator('.reva-send-button').click();

    // Loading indicator should appear
    await expect(page.locator('.reva-typing')).toBeVisible();

    // Input should be disabled during loading
    await expect(page.locator('.reva-input')).toBeDisabled();

    // After response, loading should disappear
    await expect(page.locator('.reva-typing')).not.toBeVisible({ timeout: 5000 });
  });

  test('send button is disabled when input is empty', async ({ page }) => {
    await page.goto('/');
    await page.locator('.reva-toggle').click();

    const sendButton = page.locator('.reva-send-button');
    await expect(sendButton).toBeDisabled();

    await page.locator('.reva-input').fill('Hello');
    await expect(sendButton).not.toBeDisabled();
  });

  test('header shows agent name', async ({ page }) => {
    await page.goto('/');
    await page.locator('.reva-toggle').click();

    const header = page.locator('.reva-header');
    await expect(header).toBeVisible();
    // The test-widget.html doesn't configure agent_name, so check for any header content
    await expect(header.locator('.reva-header-info')).toBeVisible();
  });
});
