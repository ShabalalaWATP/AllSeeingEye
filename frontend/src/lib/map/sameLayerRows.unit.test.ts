import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { sameLayerRows } from './sameLayerRows';
import { buildIconLayer } from '@/features/globe/layers/icons';

it('retains immutable row buffers but invalidates changed positions, order and length', () => {
  const first = liveEvent({ category: 'aviation' });
  const second = liveEvent({ id: 'second', category: 'aviation' });
  const before = buildIconLayer([first, second], vi.fn(), null)!;
  const selected = buildIconLayer([first, second], vi.fn(), first.id)!;
  expect(before.props.data).not.toBe(selected.props.data);
  expect(selected.props.dataComparator?.(before.props.data, selected.props.data)).toBe(true);
  expect(selected.props.updateTriggers.getSize).toEqual([first.id]);
  expect(sameLayerRows([first, second], [second, first])).toBe(false);
  expect(sameLayerRows([first], [{ ...first, point: { lon: 1, lat: 2 } }])).toBe(false);
  expect(sameLayerRows([first], [])).toBe(false);
  expect(sameLayerRows(undefined, [])).toBe(false);
  expect(sameLayerRows(first, first)).toBe(true);
});
