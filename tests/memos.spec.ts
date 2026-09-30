import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * The memo list, driven the way a person drives it: type, click the button with the name on
 * it, read the list. Every locator here is a role or a label rather than a CSS class, which
 * is what `docs/adr/0001` promised the app would keep stable.
 *
 * Each test starts by registering through the real form, so signing in is exercised on every
 * run rather than stubbed. That is also what makes the cookie, the Vite proxy and Postgres
 * all part of what these tests prove.
 */

const ACCOUNT = { email: 'memo@example.com', password: 'correct-horse' };

/** The memo titles, in the order the list shows them. */
function titles(page: Page) {
  return page.getByRole('heading', { level: 2 });
}

async function addMemo(page: Page, title: string, body = '') {
  const composer = page.getByRole('form', { name: 'New memo' });
  await composer.getByLabel('Title').fill(title);
  if (body !== '') {
    await composer.getByLabel('Body').fill(body);
  }
  await composer.getByRole('button', { name: 'Add memo' }).click();
  // Nothing else in the test can proceed until the new Memo is on screen, so wait here
  // rather than leaving each assertion to time out on its own.
  await expect(titles(page).filter({ hasText: title })).toBeVisible();
}

test.beforeEach(async ({ page, request }) => {
  // A known starting state. This route exists only while ENV=test, which the E2E backend
  // sets - see docs/adr/0001. Going through it rather than reusing an account is what keeps
  // one test's Memos out of the next test's list.
  const reset = await request.post('/api/__test__/reset');
  expect(reset.ok()).toBe(true);

  await page.goto('/register');
  const form = page.getByRole('form', { name: 'Create account' });
  await form.getByLabel('Email').fill(ACCOUNT.email);
  await form.getByLabel('Password').fill(ACCOUNT.password);
  await form.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL('/');
});

test('a memo is still there after a reload', async ({ page }) => {
  await addMemo(page, 'Groceries', 'milk and eggs');

  // The session cookie is httpOnly, so the page cannot re-authenticate itself with it. If
  // it survives a reload, it is genuinely being sent by the browser.
  await page.reload();

  await expect(page.getByRole('heading', { level: 2, name: 'Groceries' })).toBeVisible();
  await expect(page.getByText('milk and eggs')).toBeVisible();
});

test('the newest memo leads the list', async ({ page }) => {
  await addMemo(page, 'Groceries');
  await addMemo(page, 'Milk');

  await expect(titles(page)).toContainText(['Milk', 'Groceries']);
});

test('a pinned memo leads even a memo that was written later', async ({ page }) => {
  await addMemo(page, 'Groceries');
  await addMemo(page, 'Milk');
  await expect(titles(page)).toContainText(['Milk', 'Groceries']);

  await page.getByRole('button', { name: 'Pin Groceries' }).click();

  await expect(titles(page)).toContainText(['Groceries', 'Milk']);
});

test('unpinning returns a memo to the order it was written in', async ({ page }) => {
  await addMemo(page, 'Groceries');
  await addMemo(page, 'Milk');
  await page.getByRole('button', { name: 'Pin Groceries' }).click();
  await expect(titles(page)).toContainText(['Groceries', 'Milk']);

  // Pinning is not an edit (see docs/adr/0002), so unpinning leaves `Groceries` where it
  // was written - below `Milk` - rather than at the top of the list.
  await page.getByRole('button', { name: 'Unpin Groceries' }).click();

  await expect(titles(page)).toContainText(['Milk', 'Groceries']);
});

test('editing a memo moves it to the top of the list', async ({ page }) => {
  await addMemo(page, 'Groceries', 'milk');
  await addMemo(page, 'Milk');

  await page.getByRole('button', { name: 'Edit Groceries' }).click();
  const form = page.getByRole('form', { name: 'Edit Groceries' });
  await form.getByLabel('Body').fill('milk and eggs');
  await form.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('milk and eggs')).toBeVisible();
  await expect(titles(page)).toContainText(['Groceries', 'Milk']);
});

test('search narrows the list to what matches', async ({ page }) => {
  await addMemo(page, 'Groceries', 'milk and eggs');
  await addMemo(page, 'Call the dentist');

  await page.getByRole('searchbox').fill('milk');

  await expect(titles(page)).toContainText(['Groceries']);
  await expect(page.getByRole('heading', { level: 2 })).toHaveCount(1);
});

test('deleting a memo removes it for good', async ({ page }) => {
  await addMemo(page, 'Groceries');

  // Deleting is permanent, so the app asks first - and the test has to answer.
  page.on('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Delete Groceries' }).click();

  await expect(page.getByRole('heading', { level: 2 })).toHaveCount(0);
  await expect(page.getByText('No memos yet. Write one above.')).toBeVisible();

  await page.reload();
  await expect(page.getByText('No memos yet. Write one above.')).toBeVisible();
});
