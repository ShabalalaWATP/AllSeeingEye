import { expect, test as base, type Route } from '@playwright/test';

import { BrowserAuth, firstUser, tokenFor } from './auth';
import { baseReads, profile } from './baseData';
import { BROWSER_NOW, BROWSER_ORIGIN } from './origin';

export function barrier() {
  let release: () => void = () => undefined;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

type Handler = (route: Route) => Promise<void>;
export class BrowserApi {
  readonly auth = new BrowserAuth();
  readonly requests: string[] = [];
  readonly violations: string[] = [];
  readonly handlers = new Map<string, Handler>();
  readonly externalFixtures = new Map<string, Handler>();
  readonly blockedProviders: RegExp[] = [];
  private readonly releases: (() => void)[] = [];

  hold(key: string) {
    const entered = barrier();
    const resumed = barrier();
    this.releases.push(resumed.release);
    this.handlers.set(key, async (route) => {
      entered.release();
      await resumed.promise;
      await this.respond(route);
    });
    return { entered: entered.promise, release: resumed.release };
  }

  releasePending() {
    for (const release of this.releases) release();
  }

  async respond(route: Route) {
    const path = new URL(route.request().url()).pathname;
    if (await this.auth.route(route, path)) return;
    if (route.request().method() === 'GET') {
      if (path === '/api/me/profile') {
        await route.fulfill({ json: { ...profile, display_name: this.auth.user?.display_name } });
        return;
      }
      if (Object.hasOwn(baseReads, path)) {
        await route.fulfill({ json: baseReads[path] });
        return;
      }
      if (path === '/api/bell') {
        await route.fulfill({
          json: {
            window_days: 7,
            alerts: { items: [], total: 0, muted: false },
            mentions: { items: [], unread: 0, muted: false },
            preferences: { muted_kinds: [], muted_rules: [] },
          },
        });
        return;
      }
    }
    this.violations.push(`${route.request().method()} ${path}`);
    await route.fulfill({
      status: 501,
      json: { error: { code: 'missing_browser_fixture', message: path } },
    });
  }
}

export const test = base.extend<{ api: BrowserApi }>({
  api: [
    async ({ context }, use, testInfo) => {
      const api = new BrowserApi();
      await context.route('**/*', async (route) => {
        const url = new URL(route.request().url());
        if (url.origin !== BROWSER_ORIGIN) {
          if (
            route.request().method() === 'GET' &&
            api.blockedProviders.some((provider) => provider.test(url.href))
          ) {
            api.requests.push(`Blocked provider: ${url.origin}${url.pathname}`);
            await route.abort('blockedbyclient');
            return;
          }
          const fixture = api.externalFixtures.get(url.href);
          if (fixture && route.request().method() === 'GET') {
            api.requests.push(`Synthetic external fixture: ${url.origin}${url.pathname}`);
            await fixture(route);
            return;
          }
          api.violations.push(`External request: ${url.origin}${url.pathname}`);
          await route.abort('blockedbyclient');
          return;
        }
        if (!url.pathname.startsWith('/api/')) {
          await route.continue();
          return;
        }
        const key = `${route.request().method()} ${url.pathname}`;
        api.requests.push(key);
        if (!url.pathname.startsWith('/api/auth/') && key !== 'GET /api/site') {
          const user = api.auth.user;
          if (
            user === null ||
            route.request().headers().authorization !== `Bearer ${tokenFor(user).access_token}`
          ) {
            api.violations.push(`Wrong account authority: ${key}`);
            await route.fulfill({
              status: 401,
              json: { error: { code: 'unauthenticated', message: 'Wrong fixture account.' } },
            });
            return;
          }
        }
        const handler = api.handlers.get(key);
        await (handler ? handler(route) : api.respond(route));
      });
      await context.routeWebSocket('**/*', async (socket) => {
        api.violations.push('Unexpected WebSocket');
        await socket.close();
      });
      await use(api);
      api.releasePending();
      await testInfo.attach('synthetic-api-requests', {
        body: JSON.stringify({ requests: api.requests, violations: api.violations }, null, 2),
        contentType: 'application/json',
      });
      expect(api.violations, 'Every API must be mocked and every provider blocked').toEqual([]);
    },
    { auto: true },
  ],
});

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(BROWSER_NOW);
});

export async function signIn(
  page: import('@playwright/test').Page,
  path: string,
  email = firstUser.email,
) {
  await page.goto(path);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill('synthetic-browser-passphrase');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Logout', exact: true })).toBeVisible();
}

export { expect };
