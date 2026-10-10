import { expect, signIn, test } from './fixture';

test('native navigation confirmation preserves cancelled edits and discards an accepted departure', async ({
  page,
}) => {
  await signIn(page, '/research?brief=new');
  await page.getByLabel('Brief title', { exact: true }).fill('Private port review');
  await page
    .getByLabel('Main research question', { exact: true })
    .fill('Which terminals reopened?');
  const dismiss = page.waitForEvent('dialog').then(async (dialog) => {
    expect(dialog.type()).toBe('confirm');
    expect(dialog.message()).toMatch(/unsaved.*brief/i);
    await dialog.dismiss();
  });
  await page.getByRole('link', { name: 'Choose a saved brief', exact: true }).click();
  await dismiss;
  await expect(page).toHaveURL(/\/research\?brief=new$/);
  await expect(page.getByLabel('Brief title', { exact: true })).toHaveValue('Private port review');
  const accept = page.waitForEvent('dialog').then((dialog) => dialog.accept());
  await page.getByRole('link', { name: 'Choose a saved brief', exact: true }).click();
  await accept;
  await expect(
    page.getByRole('heading', { name: 'My Research Briefs', exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page.getByLabel('Brief title', { exact: true })).toHaveValue('');
  await expect(page.getByLabel('Main research question', { exact: true })).toHaveValue('');
});
