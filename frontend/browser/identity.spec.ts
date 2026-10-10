import { secondUser } from './auth';
import { expect, signIn, test } from './fixture';

test('logout removes private drafts immediately and serialises replacement login cookies', async ({
  page,
  api,
  context,
}) => {
  // Replacement sign-in lands on the normal globe home. Its style is empty and
  // synthetic, so MapLibre needs no tiles, glyphs, sprites or provider responses.
  api.externalFixtures.set('https://tiles.openfreemap.org/styles/dark', async (route) => {
    await route.fulfill({ json: { version: 8, sources: {}, layers: [] } });
  });
  // The default globe can begin its separate raster layer before navigation away.
  // Its known tile URLs are always aborted, never sent to the provider.
  api.blockedProviders.push(
    /^https:\/\/tiles\.maps\.eox\.at\/wmts\/1\.0\.0\/s2cloudless-2024_3857\/default\/g\/\d+\/\d+\/\d+\.jpg$/,
  );
  api.handlers.set('GET /api/events', async (route) => {
    await route.fulfill({ json: { items: [], count: 0 } });
  });
  api.handlers.set('GET /api/events/stats', async (route) => {
    await route.fulfill({
      json: { total: 0, estimated_bytes: 0, budget_bytes: 1_048_576, per_category: [] },
    });
  });
  api.handlers.set('GET /api/stream', async (route) => {
    await route.fulfill({ status: 503 });
  });
  await signIn(page, '/research?brief=new');
  const privateTitle = 'First analyst private draft';
  await page.getByLabel('Brief title', { exact: true }).fill(privateTitle);
  const logout = api.hold('POST /api/auth/logout');
  await page.getByRole('button', { name: 'Logout', exact: true }).click();
  await logout.entered;
  await expect(page.getByLabel('Email', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Brief title', { exact: true })).toHaveCount(0);
  await page.getByLabel('Email', { exact: true }).fill(secondUser.email);
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-passphrase');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Signing in…', exact: true })).toBeDisabled();
  expect(api.requests.filter((key) => key === 'POST /api/auth/login')).toHaveLength(1);
  logout.release();
  await expect(page.getByRole('button', { name: 'Logout', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Research', exact: true }).click();
  await page.getByRole('link', { name: 'Create a Research Brief', exact: true }).click();
  await expect(page.getByLabel('Brief title', { exact: true })).toHaveValue('');
  expect(api.auth.user?.id).toBe(secondUser.id);
  expect((await context.cookies()).find((cookie) => cookie.name === 'ase_csrf')?.value).toBe(
    `browser-${secondUser.id}`,
  );
  await page.reload();
  await expect(page.getByLabel('Brief title', { exact: true })).toHaveValue('');
  expect(api.requests.filter((key) => key === 'POST /api/auth/refresh')).toHaveLength(1);
  expect(api.auth.user?.id).toBe(secondUser.id);
});
