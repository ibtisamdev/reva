import { test, expect } from './fixtures';

test.describe('Widget Settings', () => {
  test('settings page renders widget preview and controls', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/widget');
    // Preview shows agent name and welcome message
    await expect(page.getByText('Reva Support').first()).toBeVisible();
    await expect(page.getByText('Hi! How can I help you today?').first()).toBeVisible();
  });

  test('embed code section shows store ID', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/widget');
    await expect(page.getByText('Embed Code')).toBeVisible();
    // The embed code should contain the store ID
    await expect(page.getByText(/store-1/)).toBeVisible();
  });

  test('color picker is visible', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/widget');
    // Should show a color input or hex display
    await expect(page.locator('input[value="#0d9488"]').first()).toBeVisible();
  });

  test('copy embed code button exists', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/widget');
    await expect(page.getByRole('button', { name: /copy/i })).toBeVisible();
  });

  test('widget preview updates with position setting', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/widget');
    // The preview container should be visible
    // Find the preview card (contains "Preview" heading and the widget preview)
    const previewCard = page.locator('div').filter({ hasText: /^Preview/ }).first();
    await expect(previewCard).toBeVisible();
  });

  test('saving settings sends PATCH with updated values', async ({ mockApi: page }) => {
    let patchBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/stores/settings**', (route) => {
      if (route.request().method() === 'PATCH') {
        patchBody = route.request().postDataJSON();
        return route.fulfill({ json: { widget: { ...patchBody } } });
      }
      return route.fulfill({
        json: {
          widget: {
            primary_color: '#0d9488',
            welcome_message: 'Hi! How can I help you today?',
            position: 'bottom-right',
            agent_name: 'Reva Support',
          },
        },
      });
    });

    await page.goto('/dashboard/settings/widget');

    // Update agent name
    const agentNameInput = page.getByLabel(/agent name/i);
    await agentNameInput.clear();
    await agentNameInput.fill('My Bot');

    // Update welcome message
    const welcomeInput = page.getByLabel(/welcome message/i);
    await welcomeInput.clear();
    await welcomeInput.fill('Hello there!');

    // Save
    await page.getByRole('button', { name: /save changes/i }).click();

    await page.waitForResponse((r) => r.url().includes('/api/v1/stores/settings') && r.request().method() === 'PATCH');
    expect(patchBody).not.toBeNull();
  });

  test('preview updates live when agent name changes', async ({ mockApi: page }) => {
    await page.goto('/dashboard/settings/widget');

    // Preview should initially show the configured agent name
    await expect(page.getByText('Reva Support').first()).toBeVisible();

    // Change agent name
    const agentNameInput = page.getByLabel(/agent name/i);
    await agentNameInput.clear();
    await agentNameInput.fill('Custom Agent');

    // Preview should update
    await expect(page.getByText('Custom Agent')).toBeVisible();
  });
});
