import { expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { prepareCyberMap, useCyberFiltersStore } from './cyberFilters';
import { useEventsStore } from './events';

it('starts off and explicitly prepares a filtered country visit without modifying event geometry', () => {
  applySession('user');
  expect(useEventsStore.getState().hidden).toContain('cyber');
  expect(useCyberFiltersStore.getState().countryContext).toBe(false);
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

it('discards pending selections and filters across every account and access transition', () => {
  applySession('user');
  prepareCyberMap({ query: 'private selection' });
  applySession('anonymous');
  applySession('user');
  expect(useCyberFiltersStore.getState()).toMatchObject({
    pending: null,
    query: '',
    countryContext: false,
  });
  prepareCyberMap();
  invalidateWorkspaceAccess();
  expect(useCyberFiltersStore.getState().pending).toBeNull();
});
