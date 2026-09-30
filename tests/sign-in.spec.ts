import { expect, test } from '@playwright/test';

/**
 * The tests that need no account, and therefore no database: a signed-out visitor is sent
 * to the sign-in page, the form is there to use, and the API answers on the app's own
 * origin. The last one is the one that would catch the proxy being misconfigured, which is
 * the failure that would otherwise break every other test for a confusing reason.
 */
test.describe('signing in', () => {
  test('a visitor who is not signed in is sent to the sign-in page', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveURL('/sign-in');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  });

  test('the sign-in form asks for an email and a password', async ({ page }) => {
    await page.goto('/sign-in');

    const form = page.getByRole('form', { name: 'Sign in' });
    await expect(form.getByLabel('Email')).toBeVisible();
    await expect(form.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeEnabled();
  });

  test('the API answers on the same origin as the app', async ({ request }) => {
    const response = await request.get('/api/health');

    expect(response.ok()).toBe(true);
  });
});
