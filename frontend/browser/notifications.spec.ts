import { bellAlerts, bellSummary } from '../src/test/fixtures.bell';

import { barrier, expect, signIn, test } from './fixture';
import { OTHER_REPORT_ID, REPORT_ID, serveReports } from './reportData';

test('notifications await acknowledgement and authorise destination navigation separately', async ({
  page,
  api,
}) => {
  serveReports(api);
  const alerts = bellAlerts(2);
  const [first, second] = alerts;
  if (!first || !second) throw new Error('The notification fixture needs two alerts.');
  let remaining = [...alerts];
  let acknowledgement: unknown;
  const entered = barrier();
  const release = barrier();
  api.handlers.set('GET /api/bell', async (route) => {
    await route.fulfill({ json: bellSummary(remaining) });
  });
  api.handlers.set('POST /api/bell/alerts/acknowledge', async (route) => {
    acknowledgement = route.request().postDataJSON() as unknown;
    entered.release();
    await release.promise;
    remaining = [second];
    await route.fulfill({ json: { acknowledged: [first.id], failed: [] } });
  });
  api.handlers.set(`GET /api/bell/alerts/${second.id}/destination`, async (route) => {
    await route.fulfill({
      json: {
        kind: 'report',
        available: true,
        report_id: OTHER_REPORT_ID,
        monitor_id: null,
        transition_id: null,
        message: null,
      },
    });
  });
  await signIn(page, `/reports/${REPORT_ID}?version=1`);
  await expect(page.getByRole('heading', { name: 'Port editions', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Notifications, 2 unread', exact: true }).click();
  const panel = page.getByRole('dialog', { name: 'Notifications' });
  const acknowledge = panel.getByRole('button', { name: 'Acknowledge Alert 1', exact: true });
  try {
    await acknowledge.click();
    await entered.promise;
    await expect(acknowledge).toHaveAttribute('aria-disabled', 'true');
    await expect(
      page.getByRole('button', { name: 'Notifications, 2 unread', exact: true }),
    ).toBeVisible();
    expect(acknowledgement).toEqual({ alert_ids: [first.id] });
  } finally {
    release.release();
  }
  await expect(
    page.getByRole('button', { name: 'Notifications, 1 unread', exact: true }),
  ).toBeVisible();
  await expect(panel.getByRole('button', { name: /^Alert 1/ })).toHaveCount(0);
  await expect(panel.getByRole('heading', { name: /Alerts to review/ })).toBeFocused();
  await panel.getByRole('button', { name: /^Alert 2/ }).click();
  await expect(page).toHaveURL(new RegExp(`/reports/${OTHER_REPORT_ID}$`));
  await expect(page.getByRole('heading', { name: 'Alert destination', exact: true })).toBeVisible();
  await expect(panel).toHaveCount(0);
  expect(api.requests.filter((key) => key === 'POST /api/bell/alerts/acknowledge')).toHaveLength(1);
});
