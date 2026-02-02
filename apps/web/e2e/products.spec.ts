import { test, expect, mockData } from './fixtures';

test.describe('Products', () => {
  test('page loads with title and description', async ({ mockApi: page }) => {
    await page.goto('/dashboard/products');
    await expect(page.locator('h1').filter({ hasText: /products/i })).toBeVisible();
  });

  test('renders product cards with titles and prices', async ({ mockApi: page }) => {
    await page.goto('/dashboard/products');
    await expect(page.getByText('Test Widget')).toBeVisible();
    await expect(page.getByText('$29.99')).toBeVisible();
    await expect(page.getByText('Plain Product')).toBeVisible();
    await expect(page.getByText('$9.99')).toBeVisible();
  });

  test('shows empty state when no products', async ({ mockApi: page }) => {
    await page.route('**/api/v1/products**', (route) => {
      return route.fulfill({ json: mockData.paginated([]) });
    });

    await page.goto('/dashboard/products');
    await expect(page.getByText(/no products synced/i)).toBeVisible();
  });

  test('shows Edit in Shopify links when connected', async ({ mockApi: page }) => {
    await page.goto('/dashboard/products');
    const links = page.getByText('Edit in Shopify');
    await expect(links.first()).toBeVisible();
  });
});
