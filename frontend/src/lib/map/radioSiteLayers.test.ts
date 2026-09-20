import { expect, it } from 'vitest';
import { TextLayer } from '@deck.gl/layers';
import { radioSiteLayers } from './radioSiteLayers';

it('retains polar sites on the globe but omits positions outside the flat map projection', () => {
  const names = { origin: '', receiver: 'Éire hill' };
  expect(radioSiteLayers(null, null, names, true)).toEqual([]);
  expect(radioSiteLayers(null, [0, 86], names, true)).toEqual([]);
  const globe = radioSiteLayers(null, [0, 86], names, false);
  expect(globe[0]!.props.data).toEqual([{ point: [0, 86], label: 'RX · Éire hill' }]);
  const label = globe.find((layer) => layer instanceof TextLayer);
  expect(label?.props.characterSet).toBe('auto');
});

it('distinguishes named transmitters and unnamed receivers without requiring an analysis', () => {
  const layers = radioSiteLayers([1, 52], [2, 53], { origin: 'Hill', receiver: '' }, true);
  expect(layers[0]!.props.data).toEqual([
    { point: [1, 52], label: 'TX · Hill' },
    { point: [2, 53], label: 'RX' },
  ]);
  expect(layers.every((layer) => layer.props.pickable === false)).toBe(true);
});
