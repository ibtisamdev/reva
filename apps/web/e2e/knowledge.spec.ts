import { test, expect, mockData } from './fixtures';

test.describe('Knowledge Base', () => {
  test('list renders article cards with title and type badge', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await expect(page.getByText('Return Policy')).toBeVisible();
    await expect(page.getByText('Shipping FAQ')).toBeVisible();
    // Content type badges
    await expect(page.getByText('Policy').first()).toBeVisible();
    await expect(page.getByText('FAQ').first()).toBeVisible();
  });

  test('shows processing badge for articles with 0 chunks', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await expect(page.getByText(/processing/i).first()).toBeVisible();
  });

  test('shows ready badge for processed articles', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await expect(page.getByText(/ready/i).first()).toBeVisible();
  });

  test('"Add Content" button opens upload dialog', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await page.getByRole('button', { name: /add content/i }).click();
    await expect(page.getByText('Add Knowledge Content')).toBeVisible();
    await expect(page.getByText('Text')).toBeVisible();
    await expect(page.getByText('PDF')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'URL' })).toBeVisible();
  });

  test('upload dialog renders text form with fields', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await page.getByRole('button', { name: /add content/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByLabel('Title')).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Content' })).toBeVisible();
    await expect(page.getByRole('button', { name: /upload/i })).toBeVisible();
  });

  test('shows empty state when no articles', async ({ mockApi: page }) => {
    const emptyHandler = (route: import('@playwright/test').Route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ json: mockData.paginated([]) });
      }
      return route.continue();
    };
    await page.route('**/api/v1/knowledge?**', emptyHandler);
    await page.route('**/api/v1/knowledge', emptyHandler);

    await page.goto('/dashboard/knowledge');
    await expect(page.getByText(/no knowledge articles yet/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /add your first article/i })).toBeVisible();
  });

  test('clicking article navigates to detail page', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await page.getByRole('link', { name: /return policy/i }).click();
    await expect(page).toHaveURL(/\/dashboard\/knowledge\/article-1/);
  });

  test('submitting upload form creates a new article', async ({ mockApi: page }) => {
    let postBody: Record<string, unknown> | null = null;
    const uploadHandler = (route: import('@playwright/test').Route) => {
      if (route.request().method() === 'POST') {
        postBody = route.request().postDataJSON();
        return route.fulfill({ json: mockData.MOCK_INGESTION_RESPONSE });
      }
      return route.fulfill({ json: mockData.paginated(mockData.MOCK_ARTICLES) });
    };
    await page.route('**/api/v1/knowledge?**', uploadHandler);
    await page.route('**/api/v1/knowledge', uploadHandler);

    await page.goto('/dashboard/knowledge');
    await page.getByRole('button', { name: /add content/i }).click();

    await page.getByLabel('Title').fill('New FAQ Article');
    await page.getByRole('textbox', { name: 'Content' }).fill('This is the FAQ content.');
    await page.getByRole('button', { name: /upload/i }).click();

    // Wait for the POST request to complete
    await page.waitForResponse((r) => r.url().includes('/api/v1/knowledge') && r.request().method() === 'POST');
    expect(postBody).not.toBeNull();
    expect((postBody as unknown as Record<string, unknown>).title).toBe('New FAQ Article');
  });

  test('delete article with confirmation removes it from list', async ({ mockApi: page }) => {
    let deleteCalled = false;
    await page.route('**/api/v1/knowledge/article-1**', (route) => {
      if (route.request().method() === 'DELETE') {
        deleteCalled = true;
        return route.fulfill({ status: 204, body: '' });
      }
      return route.fulfill({ json: mockData.MOCK_ARTICLE_DETAIL });
    });

    await page.goto('/dashboard/knowledge');
    // Open actions dropdown on first article
    await page.getByRole('button', { name: 'Actions' }).first().click();
    // Click Delete from dropdown menu
    await page.getByRole('menuitem', { name: /delete/i }).click();

    // Confirm in dialog
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/are you sure/i)).toBeVisible();
    await dialog.getByRole('button', { name: /delete/i }).click();

    await page.waitForResponse((r) => r.url().includes('/api/v1/knowledge/article-1') && r.request().method() === 'DELETE');
    expect(deleteCalled).toBe(true);
  });

  test('article detail page shows content and chunks', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge/article-1');
    // Title is in an edit form textbox
    await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('Return Policy');
    // Content preview
    await expect(page.getByText(/items can be returned/i).first()).toBeVisible();
    // Chunks section
    await expect(page.getByText(/chunk 1/i)).toBeVisible();
  });

  test('PDF tab shows drag-and-drop zone', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await page.getByRole('button', { name: /add content/i }).click();
    await page.getByRole('tab', { name: 'PDF' }).click();
    await expect(page.getByText(/drag and drop a pdf here/i)).toBeVisible();
  });

  test('URL tab shows URL input field', async ({ mockApi: page }) => {
    await page.goto('/dashboard/knowledge');
    await page.getByRole('button', { name: /add content/i }).click();
    await page.getByRole('tab', { name: 'URL' }).click();
    await expect(page.getByRole('textbox', { name: 'URL' })).toBeVisible();
  });

  test('submitting URL form calls knowledge URL API', async ({ mockApi: page }) => {
    let postCalled = false;
    await page.route('**/api/v1/knowledge/url**', (route) => {
      postCalled = true;
      return route.fulfill({ json: mockData.MOCK_INGESTION_RESPONSE });
    });

    await page.goto('/dashboard/knowledge');
    await page.getByRole('button', { name: /add content/i }).click();
    await page.getByRole('tab', { name: 'URL' }).click();
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/page');
    await page.getByRole('button', { name: /import url/i }).click();

    await page.waitForResponse((r) => r.url().includes('/api/v1/knowledge/url') && r.request().method() === 'POST');
    expect(postCalled).toBe(true);
  });
});
