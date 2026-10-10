import type { Route } from '@playwright/test';

import type { components } from '../src/lib/api/types.gen';
import { accessTokenFor } from '../src/test/accessTokens';

import { BROWSER_NOW } from './origin';

type User = components['schemas']['UserOut'];
export const firstUser: User = {
  id: '22222222-2222-4222-8222-222222222222',
  email: 'first@example.test',
  display_name: 'First Browser Analyst',
  role: 'user',
  is_active: true,
  created_at: BROWSER_NOW.toISOString(),
  last_login_at: null,
};
export const secondUser: User = {
  ...firstUser,
  id: '33333333-3333-4333-8333-333333333333',
  email: 'second@example.test',
  display_name: 'Second Browser Analyst',
};

export function tokenFor(user: User): components['schemas']['TokenResponse'] {
  return {
    access_token: accessTokenFor(user.id),
    token_type: 'bearer',
    expires_in: 900,
    user,
    activity: {
      server_now: BROWSER_NOW.toISOString(),
      last_activity_at: BROWSER_NOW.toISOString(),
      idle_expires_at: new Date(BROWSER_NOW.getTime() + 180 * 60_000).toISOString(),
      idle_minutes: 180,
    },
  };
}

/** Synthetic API authentication only. No server, credentials or application-store injection. */
export class BrowserAuth {
  user: User | null = null;

  async route(route: Route, path: string): Promise<boolean> {
    if (path === '/api/auth/login' && route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { email: string };
      this.user = body.email === secondUser.email ? secondUser : firstUser;
      await route.fulfill({
        json: tokenFor(this.user),
        headers: { 'set-cookie': `ase_csrf=browser-${this.user.id}; Path=/; SameSite=Lax` },
      });
      return true;
    }
    if (path === '/api/auth/logout' && route.request().method() === 'POST') {
      this.user = null;
      await route.fulfill({
        status: 204,
        headers: { 'set-cookie': 'ase_csrf=; Path=/; Max-Age=0; SameSite=Lax' },
      });
      return true;
    }
    if (path === '/api/auth/refresh' && route.request().method() === 'POST') {
      await route.fulfill(
        this.user === null
          ? { status: 401, json: { error: { code: 'invalid_refresh', message: 'Sign in.' } } }
          : { json: tokenFor(this.user) },
      );
      return true;
    }
    if (path === '/api/me' && route.request().method() === 'GET') {
      await route.fulfill({ json: this.user });
      return true;
    }
    return false;
  }
}
