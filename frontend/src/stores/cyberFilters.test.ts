import { expect, it } from 'vitest';
import { applySession } from '@/test/session';
import { liveEvent } from '@/test/fixtures';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from './auth';
import { prepareCyberMap, useCyberFiltersStore } from './cyberFilters';
import { useEventsStore } from './events';

// Real session transitions capture browser cookies, so these need the DOM test lane.
it('keeps Cyber off with country context ready, and prepares a visit without changing geometry', () => {
  applySession('user');
  expect(useEventsStore.getState().hidden).toContain('cyber');
  expect(useCyberFiltersStore.getState().countryContext).toBe(true);
  const event = liveEvent({
    category: 'cyber',
    geo_confidence: 'country',
    point: null,
    country_iso: 'GB',
  });
  expect(
    prepareCyberMap({ country: 'GB', days: 7, kind: 'ransomware_claim', query: 'bank', event }),
  ).toBe('/');
  expect(useEventsStore.getState()).toMatchObject({ country: 'GB', windowHours: 168, byId: {} });
  expect(useEventsStore.getState().hidden).not.toContain('cyber');
  expect(useCyberFiltersStore.getState()).toMatchObject({
    kind: 'ransomware_claim',
    query: 'bank',
    countryContext: true,
    pending: { country: 'GB', event },
  });
  expect(event.point).toBeNull();
  prepareCyberMap();
  expect(useEventsStore.getState().hidden).not.toContain('cyber');
  useCyberFiltersStore.getState().consumeFocus();
  expect(useCyberFiltersStore.getState().pending).toBeNull();
});

it('resets private map selections when a cookie-backed replacement account signs in', () => {
  document.cookie = 'ase_csrf=first-cyber-session; Path=/';
  applySession('user');
  expect(useAuthStore.getState().sessionCsrf).toBe('first-cyber-session');
  prepareCyberMap({ kind: 'ransomware_claim', query: 'private selection' });
  expect(useCyberFiltersStore.getState().pending).not.toBeNull();

  document.cookie = 'ase_csrf=replacement-cyber-session; Path=/';
  applySession('admin');
  expect(useAuthStore.getState().sessionCsrf).toBe('replacement-cyber-session');
  expect(useCyberFiltersStore.getState()).toMatchObject({
    pending: null,
    kind: 'all',
    query: '',
    countryContext: true,
  });
});

it('discards pending selections and filters across every account and access transition', () => {
  applySession('user');
  prepareCyberMap({ query: 'private selection' });
  applySession('anonymous');
  applySession('user');
  expect(useCyberFiltersStore.getState()).toMatchObject({
    pending: null,
    query: '',
    countryContext: true,
  });
  prepareCyberMap();
  invalidateWorkspaceAccess();
  expect(useCyberFiltersStore.getState().pending).toBeNull();
});
