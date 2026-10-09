import { expect, it } from 'vitest';
import { initialCapabilitiesState, useCapabilitiesStore } from '@/stores/capabilities';
import { basemapUnavailable, mapSourceAllowed, LICENCE_UNAVAILABLE } from './sourcePolicy';

it('blocks provider requests until installation policy is known, including on lookup failure', () => {
  useCapabilitiesStore.setState(initialCapabilitiesState);
  expect(mapSourceAllowed('map:eox_s2cloudless')).toBe(false);
  useCapabilitiesStore.setState({ loaded: true, commercialUse: false, error: 'Policy unavailable' });
  expect(mapSourceAllowed('map:eox_s2cloudless')).toBe(false);
});

it('permits the default mode but fails closed for unknown commercial source IDs', () => {
  useCapabilitiesStore.setState({ loaded: true, commercialUse: false });
  expect(mapSourceAllowed('map:eox_s2cloudless')).toBe(true);
  useCapabilitiesStore.setState({ commercialUse: true });
  expect(mapSourceAllowed('map:eox_s2cloudless')).toBe(false);
});

it('checks vector dependencies as well as raster permission and OS configuration', () => {
  const allowed = {
    commercial_use: 'allowed' as const, attribution_required: true,
    licence_ref: 'reference', available: true, acknowledged: false, reason: 'Permitted',
  };
  useCapabilitiesStore.setState({
    loaded: true, commercialUse: true,
    sourceLicences: { 'map:openfreemap': allowed, 'map:os_maps': allowed },
  });
  expect(basemapUnavailable(useCapabilitiesStore.getState(), 'dark')).toBeNull();
  expect(basemapUnavailable(useCapabilitiesStore.getState(), 'hybrid')).toBe(LICENCE_UNAVAILABLE);
  expect(basemapUnavailable(useCapabilitiesStore.getState(), 'os_road')).toContain('not configured');
});
