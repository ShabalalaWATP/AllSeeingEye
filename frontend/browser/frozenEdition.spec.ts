import { expect, signIn, test } from './fixture';
import { FROZEN_TEXT, LATEST_TEXT, REPORT_ID, serveReports, serveSubscription } from './reportData';

test('subscription history opens and reloads its frozen edition rather than the latest', async ({
  page,
  api,
}) => {
  serveReports(api);
  serveSubscription(api);
  await signIn(page, '/subscriptions');
  await page.getByRole('button', { name: 'History', exact: true }).click();
  const history = page.getByRole('region', { name: 'Subscription history' });
  const link = history.getByRole('link', { name: 'Read report', exact: true });
  await expect(link).toHaveAttribute('href', `/reports/${REPORT_ID}?version=1`);
  await link.click();
  await expect(page).toHaveURL(new RegExp(`/reports/${REPORT_ID}\\?version=1$`));
  const analysis = page.getByRole('region', { name: 'Analysis', exact: true });
  await expect(analysis).toContainText(FROZEN_TEXT);
  await expect(analysis).not.toContainText(LATEST_TEXT);
  await expect(
    page
      .getByRole('navigation', { name: 'Versions' })
      .getByRole('link', { name: '1', exact: true }),
  ).toHaveAttribute('aria-current', 'page');
  await page.reload();
  await expect(analysis).toContainText(FROZEN_TEXT);
  await expect(analysis).not.toContainText(LATEST_TEXT);
  await page
    .getByRole('navigation', { name: 'Versions' })
    .getByRole('link', { name: '2', exact: true })
    .click();
  await expect(analysis).toContainText(LATEST_TEXT);
  await page.goBack();
  await expect(analysis).toContainText(FROZEN_TEXT);
});
