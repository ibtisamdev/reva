import { test as setup, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const AUTH_FILE = path.join(__dirname, '..', '.auth', 'user.json');

const TEST_USER = {
  name: 'E2E Test User',
  email: `e2e-test-${Date.now()}@example.com`,
  password: 'TestPassword123!',
};

setup('authenticate', async ({ page, request }) => {
  // Ensure .auth directory exists
  const authDir = path.dirname(AUTH_FILE);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Sign up a test user via API (request context, separate from page)
  await request.post('http://localhost:3000/api/auth/sign-up/email', {
    headers: { Origin: 'http://localhost:3000' },
    data: {
      name: TEST_USER.name,
      email: TEST_USER.email,
      password: TEST_USER.password,
    },
  });

  // Sign in via the browser UI so cookies land on the page context
  await page.goto('/sign-in');
  await page.getByLabel(/email/i).fill(TEST_USER.email);
  await page.getByLabel(/password/i).fill(TEST_USER.password);
  await page.getByRole('button', { name: /sign in/i }).click();

  // Wait for redirect to dashboard (indicates successful sign-in)
  await page.waitForURL('**/dashboard**', { timeout: 15000 });

  // Save storage state for reuse by other tests
  await page.context().storageState({ path: AUTH_FILE });
});
