import { expect, it } from 'vitest';

import {
  MAP_GUIDE_PANEL,
  MAP_LAYER_GROUPS,
  isMapPanel,
  mapLayerEntries,
  mapPanelHref,
  readMapPanel,
} from './mapLayerDirectory';

it('only accepts a panel the map actually defines', () => {
  expect(readMapPanel(new URLSearchParams({ panel: MAP_GUIDE_PANEL }))).toBe(MAP_GUIDE_PANEL);
  expect(readMapPanel(new URLSearchParams({ panel: 'CCTV' }))).toBe('CCTV');
  expect(readMapPanel(new URLSearchParams({ panel: '<script>' }))).toBeNull();
  expect(readMapPanel(new URLSearchParams())).toBeNull();
  expect(isMapPanel(null)).toBe(false);
});

it('links to a panel without smuggling other route parameters', () => {
  const url = new URL(mapPanelHref('Technology & communications'), 'http://local.test');
  expect(url.pathname).toBe('/');
  expect(url.searchParams.get('panel')).toBe('technology');
  expect([...url.searchParams.keys()]).toEqual(['panel']);
});

it('supports stable tool links and legacy display labels', () => {
  expect(readMapPanel(new URLSearchParams({ panel: 'rf' }))).toBe('RF link calculator');
  expect(readMapPanel(new URLSearchParams({ panel: 'RF coverage' }))).toBe('RF link calculator');
  expect(readMapPanel(new URLSearchParams({ panel: 'Measure' }))).toBe('Measure distance and area');
  expect(mapPanelHref('rf')).toBe('/?panel=rf');
  expect(mapPanelHref('missing')).toBe('/');
});

it('describes every listed layer and keeps identifiers unique', () => {
  const entries = mapLayerEntries();
  expect(entries.length).toBeGreaterThanOrEqual(MAP_LAYER_GROUPS.length);
  expect(new Set(entries.map((entry) => entry.id)).size).toBe(entries.length);
  for (const entry of entries) {
    expect(entry.description.length).toBeGreaterThan(20);
    if (entry.panel !== undefined) expect(isMapPanel(entry.panel)).toBe(true);
  }
});
