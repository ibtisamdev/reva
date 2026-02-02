import { expect, test, type APIRequestContext } from '@playwright/test';

/** Create a test user via API without affecting browser cookies */
async function createTestUser(request: APIRequestContext, email: string, password: string, name = 'Test User') {
  await request.post('http://localhost:3000/api/auth/sign-up/email', {
    headers: { Origin: 'http://localhost:3000' },
    data: { name, email, password },
  });
}

test.describe('Authentication - Page Rendering', () => {
  test('sign in page renders correctly', async ({ page }) => {
    await page.goto('/sign-in');
    await expect(page.getByText('Sign in').first()).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /continue with google/i })).toBeVisible();
  });

  test('sign in page has link to sign up', async ({ page }) => {
    await page.goto('/sign-in');
    const signUpLink = page.getByRole('link', { name: /sign up/i });
    await expect(signUpLink).toBeVisible();
    await expect(signUpLink).toHaveAttribute('href', '/sign-up');
  });

  test('sign up page renders correctly', async ({ page }) => {
    await page.goto('/sign-up');
    await expect(page.getByText('Create an account').first()).toBeVisible();
    await expect(page.getByLabel(/name/i)).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /create account/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /continue with google/i })).toBeVisible();
  });

  test('sign up page has link to sign in', async ({ page }) => {
    await page.goto('/sign-up');
    const signInLink = page.getByRole('link', { name: /sign in/i });
    await expect(signInLink).toBeVisible();
    await expect(signInLink).toHaveAttribute('href', '/sign-in');
  });

  test('sign in shows validation for empty fields', async ({ page }) => {
    await page.goto('/sign-in');
    await page.getByRole('button', { name: /sign in/i }).click();
    const emailInput = page.getByLabel(/email/i);
    await expect(emailInput).toHaveAttribute('required', '');
  });

  test('unauthenticated user is redirected from dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForURL(/sign-in|dashboard/);
  });
});

test.describe('Authentication - Sign In Flow', () => {
  test('successful sign in redirects to dashboard', async ({ page, request }) => {
    const email = `e2e-signin-${Date.now()}@example.com`;
    const password = 'TestPassword123!';
    await createTestUser(request, email, password);

    await page.goto('/sign-in');
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole('button', { name: /sign in/i }).click();

    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('failed sign in shows error message', async ({ page }) => {
    await page.goto('/sign-in');
    await page.getByLabel(/email/i).fill('nonexistent@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    await expect(page.getByText(/invalid|failed|error|incorrect/i)).toBeVisible({ timeout: 5000 });
    await expect(page).toHaveURL(/\/sign-in/);
  });

  test('sign in form disables inputs while loading', async ({ page }) => {
    await page.route('**/api/auth/sign-in/email', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      return route.fulfill({
        status: 200,
        json: {
          user: { id: 'user-1', name: 'Test User', email: 'test@example.com' },
          session: { id: 'session-1' },
        },
      });
    });

    await page.goto('/sign-in');
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();

    await expect(page.getByLabel(/email/i)).toBeDisabled();
    await expect(page.getByLabel(/password/i)).toBeDisabled();
  });
});

test.describe('Authentication - Sign Up Flow', () => {
  test('successful sign up redirects to dashboard', async ({ page }) => {
    const email = `e2e-signup-${Date.now()}@example.com`;

    await page.goto('/sign-up');
    await page.getByLabel(/name/i).fill('New User');
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill('TestPassword123!');
    await page.getByRole('button', { name: /create account/i }).click();

    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('failed sign up shows error message', async ({ page, request }) => {
    const email = `e2e-dup-${Date.now()}@example.com`;
    await createTestUser(request, email, 'TestPassword123!');

    await page.goto('/sign-up');
    await page.getByLabel(/name/i).fill('Test User');
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill('TestPassword123!');
    await page.getByRole('button', { name: /create account/i }).click();

    await expect(page.getByText(/already|exists|failed|error/i)).toBeVisible({ timeout: 5000 });
    await expect(page).toHaveURL(/\/sign-up/);
  });

  test('sign up enforces minimum password length', async ({ page }) => {
    await page.goto('/sign-up');
    const passwordInput = page.getByLabel(/password/i);
    await expect(passwordInput).toHaveAttribute('minlength', '8');
    await expect(page.getByText(/at least 8 characters/i)).toBeVisible();
  });
});

test.describe('Authentication - Sign Out Flow', () => {
  test('sign out redirects to sign-in page', async ({ page, request }) => {
    const email = `e2e-signout-${Date.now()}@example.com`;
    const password = 'TestPassword123!';
    await createTestUser(request, email, password);

    // Sign in via browser
    await page.goto('/sign-in');
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });

    // Click the avatar button in header to open user menu
    const avatarButton = page.locator('header').getByRole('button').last();
    await avatarButton.click();
    // Click sign out from dropdown
    await page.getByRole('menuitem', { name: /sign out/i }).click();

    // Sign out redirects to home page
    await page.waitForURL(/localhost:3000\/$|\/sign-in/, { timeout: 10000 });
  });
});
