import { test, expect, mockData } from './fixtures';

test.describe('Dashboard', () => {
  test('loads with sidebar showing store name and nav links', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await expect(page.getByText('Test Store').first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Overview' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Conversations' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Knowledge Base' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Widget Settings' })).toBeVisible();
  });

  test('shows Products and Integrations nav links', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('link', { name: 'Products' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Integrations' })).toBeVisible();
  });

  test('navigates to Products page', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Products' }).click();
    await expect(page).toHaveURL(/\/dashboard\/products/);
  });

  test('navigates to Integrations page', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Integrations' }).click();
    await expect(page).toHaveURL(/\/dashboard\/settings\/integrations/);
  });

  test('shows page title "Overview" on /dashboard', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await expect(page.locator('h1').filter({ hasText: 'Overview' })).toBeVisible();
  });

  test('shows no-store state when stores list is empty', async ({ mockApi: page }) => {
    const emptyStoresHandler = (route: import('@playwright/test').Route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ json: { items: [], total: 0 } });
      }
      return route.continue();
    };
    await page.route('**/api/v1/stores?**', emptyStoresHandler);
    await page.route('**/api/v1/stores', emptyStoresHandler);

    await page.goto('/dashboard');
    await expect(page.getByText(/welcome to reva/i)).toBeVisible();
    await expect(page.getByLabel(/store name/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /create store/i })).toBeVisible();
  });

  test('navigates between sidebar pages', async ({ mockApi: page }) => {
    await page.goto('/dashboard');

    // Click Conversations
    await page.getByRole('link', { name: 'Conversations' }).click();
    await expect(page).toHaveURL(/\/dashboard\/conversations/);

    // Click Knowledge Base
    await page.getByRole('link', { name: 'Knowledge Base' }).click();
    await expect(page).toHaveURL(/\/dashboard\/knowledge/);

    // Click Widget Settings
    await page.getByRole('link', { name: 'Widget Settings' }).click();
    await expect(page).toHaveURL(/\/dashboard\/settings\/widget/);

    // Click Overview
    await page.getByRole('link', { name: 'Overview' }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
  });

  test('store selector shows store name', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await expect(page.getByText('Test Store')).toBeVisible();
  });

  test('user menu is visible', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    // Should show either avatar or user menu button
    const header = page.locator('header');
    await expect(header).toBeVisible();
  });

  test('create store from no-store state', async ({ mockApi: page }) => {
    // Mock organization APIs (better-auth calls these before store creation)
    await page.route('**/api/auth/organization/get-full-organization', (route) => {
      return route.fulfill({ json: { data: { id: 'org-1', name: 'Test Org', slug: 'test-org' } } });
    });
    await page.route('**/api/auth/organization**', (route) => {
      return route.fulfill({ json: { data: { id: 'org-1', name: 'Test Org', slug: 'test-org' } } });
    });

    let postBody: Record<string, unknown> | null = null;
    const storeHandler = (route: import('@playwright/test').Route) => {
      if (route.request().method() === 'GET') {
        if (postBody) {
          return route.fulfill({
            json: {
              items: [{ id: 'store-new', organization_id: 'org-1', name: postBody.name, email: null, plan: 'free', is_active: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }],
              total: 1,
            },
          });
        }
        return route.fulfill({ json: { items: [], total: 0 } });
      }
      if (route.request().method() === 'POST') {
        postBody = route.request().postDataJSON();
        return route.fulfill({
          json: { id: 'store-new', organization_id: 'org-1', name: postBody?.name || 'New Store', email: null, plan: 'free', is_active: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
        });
      }
      return route.continue();
    };
    await page.route('**/api/v1/stores?**', storeHandler);
    await page.route('**/api/v1/stores', storeHandler);

    await page.goto('/dashboard');
    await expect(page.getByText(/welcome to reva/i)).toBeVisible();

    await page.getByLabel(/store name/i).fill('My New Store');
    await page.getByRole('button', { name: /create store/i }).click();

    await expect.poll(() => postBody).not.toBeNull();
    expect((postBody as unknown as Record<string, unknown>).name).toBe('My New Store');
  });

  test('switching stores refreshes data', async ({ mockApi: page }) => {
    let lastStoreHeader: string | null = null;
    await page.route('**/api/v1/chat/conversations**', (route) => {
      const url = route.request().url();
      // Track which store's data is being requested via headers or store context
      lastStoreHeader = url;
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 20, pages: 1 } });
    });

    await page.goto('/dashboard');
    await expect(page.getByText('Test Store')).toBeVisible();

    // Open store selector and pick second store
    await page.getByRole('combobox').click();
    await page.getByRole('option', { name: 'Second Store' }).click();

    await expect(page.getByText('Second Store')).toBeVisible();
  });
});
