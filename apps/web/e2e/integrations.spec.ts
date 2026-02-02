import { test, expect, mockData } from './fixtures';

test.describe('Integrations', () => {
  test('page loads with title', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/integrations');
    await expect(page.locator('h1').filter({ hasText: /integrations/i })).toBeVisible();
  });

  test('shows connected state with store info', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/integrations');
    await expect(page.getByText('Connected')).toBeVisible();
    await expect(page.getByText('test-store.myshopify.com')).toBeVisible();
    await expect(page.getByText('42')).toBeVisible();
    await expect(page.getByRole('button', { name: /resync products/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /disconnect/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /shopify admin/i })).toBeVisible();
  });

  test('shows disconnected state', async ({ mockApi: page }) => {
    await page.route('**/api/v1/shopify/status**', (route) => {
      return route.fulfill({
        json: { platform: 'shopify', platform_domain: '', status: 'disconnected', last_synced_at: null, product_count: 0 },
      });
    });

    await page.goto('/dashboard/settings/integrations');
    await expect(page.getByText('Not Connected')).toBeVisible();
    await expect(page.getByLabel(/shop domain/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /connect shopify/i })).toBeVisible();
  });

  test('connect flow calls install URL API', async ({ mockApi: page }) => {
    let installUrlCalled = false;
    await page.route('**/api/v1/shopify/status**', (route) => {
      return route.fulfill({
        json: { platform: 'shopify', platform_domain: '', status: 'disconnected', last_synced_at: null, product_count: 0 },
      });
    });
    await page.route('**/api/v1/shopify/install-url**', (route) => {
      installUrlCalled = true;
      const url = route.request().url();
      expect(url).toContain('shop=mystore.myshopify.com');
      return route.fulfill({ json: { install_url: 'https://mystore.myshopify.com/admin/oauth/authorize' } });
    });

    await page.goto('/dashboard/settings/integrations');
    await page.getByLabel(/shop domain/i).fill('mystore');
    await page.getByRole('button', { name: /connect shopify/i }).click();

    await page.waitForResponse((r) => r.url().includes('/api/v1/shopify/install-url'));
    expect(installUrlCalled).toBe(true);
  });

  test('resync triggers API call', async ({ mockApi: page }) => {
    let syncCalled = false;
    await page.route('**/api/v1/shopify/sync**', (route) => {
      syncCalled = true;
      return route.fulfill({ json: mockData.MOCK_SYNC_STATUS });
    });

    await page.goto('/dashboard/settings/integrations');
    await page.getByRole('button', { name: /resync products/i }).click();

    await page.waitForResponse((r) => r.url().includes('/api/v1/shopify/sync'));
    expect(syncCalled).toBe(true);
  });

  test('disconnect triggers API call', async ({ mockApi: page }) => {
    let disconnectCalled = false;
    await page.route('**/api/v1/shopify/disconnect**', (route) => {
      disconnectCalled = true;
      return route.fulfill({ json: mockData.MOCK_SYNC_STATUS });
    });

    await page.goto('/dashboard/settings/integrations');
    await page.getByRole('button', { name: /disconnect/i }).click();

    await page.waitForResponse((r) => r.url().includes('/api/v1/shopify/disconnect'));
    expect(disconnectCalled).toBe(true);
  });
});
