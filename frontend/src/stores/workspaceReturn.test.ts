import { afterEach, describe, expect, it, vi } from 'vitest';

import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

import { useAuthStore } from './auth';
import {
  ADMIN_HOME,
  RESEARCH_HOME,
  isAdminRoute,
  isResearchRoute,
  rememberAdminRoute,
  rememberResearchRoute,
  resetWorkspaceReturn,
  useWorkspaceReturnStore,
} from './workspaceReturn';

afterEach(() => {
  resetWorkspaceReturn();
  vi.restoreAllMocks();
});

const targets = () => useWorkspaceReturnStore.getState();

describe('workspace return memory', () => {
  it('starts at the globe and the administration overview', () => {
    expect(targets()).toEqual({ research: RESEARCH_HOME, admin: ADMIN_HOME });
    expect(RESEARCH_HOME).toBe('/');
    expect(ADMIN_HOME).toBe('/admin');
  });

  it('remembers the latest route of each workspace with its query', () => {
    rememberResearchRoute('/research/saved', '?q=port');
    rememberAdminRoute('/admin/users');
    rememberResearchRoute('/watches');
    expect(targets()).toEqual({ research: '/watches', admin: '/admin/users' });
    rememberAdminRoute('/admin/audit', '?actor=me');
    expect(targets().admin).toBe('/admin/audit?actor=me');
  });

  it.each([
    '/admin',
    '/admin/users',
    '/login',
    '/set-password',
    '/request-account',
    '/privacy',
    '/privacy/requests',
    '/terms',
    '/enterprise',
    '/dev/admin-preview',
    '//evil.example/path',
    '/\\evil.example',
    'relative/path',
  ])('never records %s as a research route', (pathname) => {
    rememberResearchRoute(pathname);
    expect(isResearchRoute(pathname)).toBe(false);
    expect(targets().research).toBe(RESEARCH_HOME);
  });

  it.each(['/', '/research', '/watches', '/administrator-notes', '/teams'])(
    'accepts %s as a research route',
    (pathname) => {
      expect(isResearchRoute(pathname)).toBe(true);
    },
  );

  it.each(['/', '/research', '/administrator', '//admin', '/admin\\x'])(
    'never records %s as an administration route',
    (pathname) => {
      rememberAdminRoute(pathname);
      expect(isAdminRoute(pathname)).toBe(false);
      expect(targets().admin).toBe(ADMIN_HOME);
    },
  );

  it('rejects a malformed query and an oversized route', () => {
    rememberResearchRoute('/research', 'q=1');
    rememberResearchRoute(`/research/${'x'.repeat(2100)}`);
    rememberAdminRoute('/admin/users', `?${'x'.repeat(2100)}`);
    expect(targets()).toEqual({ research: RESEARCH_HOME, admin: ADMIN_HOME });
  });

  it('forgets both places when the account changes or signs out', () => {
    useAuthStore.getState().setSession(tokenFor(adminUser));
    rememberResearchRoute('/watches');
    rememberAdminRoute('/admin/users');
    // A token rotation for the same account keeps its places.
    useAuthStore.getState().setSession(tokenFor(adminUser, { revision: 'rotated' }));
    expect(targets()).toEqual({ research: '/watches', admin: '/admin/users' });
    useAuthStore.getState().setSession(tokenFor(plainUser));
    expect(targets()).toEqual({ research: RESEARCH_HOME, admin: ADMIN_HOME });
    rememberResearchRoute('/teams');
    useAuthStore.getState().clearSession();
    expect(targets().research).toBe(RESEARCH_HOME);
  });

  it('never reads or writes browser storage', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const getItem = vi.spyOn(Storage.prototype, 'getItem');
    const before = { local: localStorage.length, session: sessionStorage.length };
    rememberResearchRoute('/research/saved', '?q=port');
    rememberAdminRoute('/admin/users');
    resetWorkspaceReturn();
    expect(setItem).not.toHaveBeenCalled();
    expect(getItem).not.toHaveBeenCalled();
    expect({ local: localStorage.length, session: sessionStorage.length }).toEqual(before);
    expect('persist' in useWorkspaceReturnStore).toBe(false);
  });
});
