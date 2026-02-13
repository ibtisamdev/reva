import { test, expect, mockData } from './fixtures';

test.describe('Order Inquiries Page', () => {
  test('navigates to Order Inquiries from sidebar', async ({ mockApi: page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Order Inquiries' }).click();
    await expect(page).toHaveURL(/\/dashboard\/orders/);
  });

  test('shows page title and description', async ({ mockApi: page }) => {
    await page.goto('/dashboard/orders');
    await expect(page.getByRole('heading', { name: 'Order Inquiries' })).toBeVisible();
    await expect(page.getByText(/WISMO analytics/)).toBeVisible();
  });

  test('displays summary cards with data', async ({ mockApi: page }) => {
    await page.goto('/dashboard/orders');

    // Wait for data to load
    await expect(page.getByText('42')).toBeVisible();
    await expect(page.getByText('85%')).toBeVisible();
    await expect(page.getByText('1.4')).toBeVisible();
    await expect(page.getByText('30 days')).toBeVisible();

    // Card titles
    await expect(page.getByText('Total Inquiries')).toBeVisible();
    await expect(page.getByText('Resolution Rate')).toBeVisible();
    await expect(page.getByText('Avg Per Day')).toBeVisible();
    await expect(page.getByText('Period')).toBeVisible();
  });

  test('displays daily trend chart', async ({ mockApi: page }) => {
    await page.goto('/dashboard/orders');

    await expect(page.getByText('Daily Trend (Last 30 Days)')).toBeVisible();
    // Trend chart should show date range
    await expect(page.getByText('2024-01-13')).toBeVisible();
    await expect(page.getByText('2024-01-15')).toBeVisible();
  });

  test('displays inquiry table with data', async ({ mockApi: page }) => {
    await page.goto('/dashboard/orders');

    await expect(page.getByText('Recent Inquiries')).toBeVisible();

    // Table headers
    await expect(page.getByText('Order #')).toBeVisible();
    await expect(page.getByText('Email')).toBeVisible();
    await expect(page.getByText('Type')).toBeVisible();
    await expect(page.getByText('Resolution')).toBeVisible();

    // Table data from mock
    await expect(page.getByText('#1001')).toBeVisible();
    await expect(page.getByText('customer@example.com')).toBeVisible();
    await expect(page.getByText('order status')).toBeVisible();
    await expect(page.getByText('answered')).toBeVisible();
    await expect(page.getByText('#1002')).toBeVisible();
    await expect(page.getByText('verification failed')).toBeVisible();
  });

  test('shows empty state when no inquiries', async ({ mockApi: page }) => {
    await page.route('**/api/v1/analytics/wismo/inquiries**', async (route) => {
      return route.fulfill({
        json: { items: [], total: 0, page: 1, page_size: 20, pages: 1 },
      });
    });

    await page.goto('/dashboard/orders');

    await expect(page.getByText(/no order inquiries yet/i)).toBeVisible();
  });

  test('shows pagination when multiple pages', async ({ mockApi: page }) => {
    const manyInquiries = Array.from({ length: 25 }, (_, i) => ({
      id: `inq-${i}`,
      customer_email: `user${i}@example.com`,
      order_number: `#${1000 + i}`,
      inquiry_type: 'order_status',
      order_status: 'paid',
      fulfillment_status: null,
      resolution: 'answered',
      created_at: '2024-01-15T10:00:00Z',
      resolved_at: '2024-01-15T10:01:00Z',
    }));

    await page.route('**/api/v1/analytics/wismo/inquiries**', async (route) => {
      return route.fulfill({
        json: {
          items: manyInquiries.slice(0, 20),
          total: 25,
          page: 1,
          page_size: 20,
          pages: 2,
        },
      });
    });

    await page.goto('/dashboard/orders');

    await expect(page.getByText('Previous')).toBeVisible();
    await expect(page.getByText('Next')).toBeVisible();
    await expect(page.getByText(/Page 1 of 2/)).toBeVisible();
  });
});
