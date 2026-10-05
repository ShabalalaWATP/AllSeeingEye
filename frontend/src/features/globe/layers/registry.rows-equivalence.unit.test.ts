import type { Layer } from '@deck.gl/core';
import { expect, it, vi } from 'vitest';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';
import { ORDERED_CATEGORIES } from '@/lib/categories';
import { geographicOrder } from '@/stores/events.geography';
import { liveEvent } from '@/test/fixtures';
import { isMappedEvent } from '../geographicPrecision';
import { CLUSTER_ZOOM, cellSizeFor, clusterEvents, type Cluster } from './clusters';
import { iconFor } from './icons';
import { buildEventLayers, type LayerView } from './registry';

interface ExpectedLayer {
  id: string;
  data: readonly (LiveEvent | Cluster)[];
}

// Independent row oracle retains the original multi-pass registry algorithm.
// Geometry, icons and clustering are shared unchanged responsibilities, not reimplemented.
function reference(
  events: readonly LiveEvent[],
  hidden: readonly Category[],
  selectedId: string | null,
  view?: LayerView,
): ExpectedLayer[] {
  const visible = events.filter(
    (event) => isMappedEvent(event) && !hidden.includes(event.category),
  );
  const exact = visible.filter((event) => event.geo_confidence === 'exact');
  const approximate = visible.filter((event) => event.geo_confidence !== 'exact');
  const layers: ExpectedLayer[] = approximate.length
    ? [{ id: 'approximate-events', data: approximate }]
    : [];
  let loose = exact;
  if (view !== undefined && view.zoom < CLUSTER_ZOOM) {
    const traffic = exact.filter((event) =>
      ['aircraft', 'vessel', 'vessel_unknown'].includes(iconFor(event) ?? ''),
    );
    const shown = geographicOrder(traffic).slice(0, 250);
    const selectedTraffic = traffic.find((event) => event.id === selectedId);
    if (selectedTraffic && !shown.includes(selectedTraffic))
      shown[shown.length - 1] = selectedTraffic;
    const ids = new Set(shown.map((event) => event.id));
    const clustered = clusterEvents(
      exact.filter((event) => !ids.has(event.id)),
      cellSizeFor(view.zoom),
    );
    if (clustered.clusters.length) {
      layers.push({ id: 'clusters', data: clustered.clusters });
      layers.push({ id: 'cluster-labels', data: clustered.clusters });
    }
    loose = [...shown, ...clustered.loose];
  }
  const byCategory = new Map<Category, LiveEvent[]>();
  for (const event of loose.filter((row) => iconFor(row) === null)) {
    const rows = byCategory.get(event.category) ?? [];
    rows.push(event);
    byCategory.set(event.category, rows);
  }
  for (const [category, data] of byCategory) layers.push({ id: `events-${category}`, data });
  const iconEvents = [
    ...loose,
    ...visible.filter(
      (event) =>
        (['conflict', 'cyber'].includes(event.category) ||
          ['wildfire', 'news'].includes(iconFor(event) ?? '')) &&
        event.geo_confidence !== 'exact',
    ),
  ].filter((event) => event.point !== null && iconFor(event) !== null);
  if (iconEvents.length) layers.push({ id: 'event-icons', data: iconEvents });
  const selected = visible.find((event) => event.id === selectedId);
  if (selected) layers.push({ id: 'selected-event-halo', data: [selected] });
  return layers;
}

function assertEquivalent(
  events: readonly LiveEvent[],
  hidden: readonly Category[] = [],
  selectedId: string | null = null,
  view?: LayerView,
): Layer[] {
  const expected = reference(events, hidden, selectedId, view);
  const actual = buildEventLayers(events, hidden, vi.fn(), selectedId, view);
  expect(actual.map((layer) => layer.id)).toEqual(expected.map((layer) => layer.id));
  actual.forEach((layer, index) => {
    const data: unknown = layer.props.data;
    expect(data).toEqual(expected[index]!.data);
    if (!Array.isArray(data)) throw new Error('Expected materialised scene rows');
    expected[index]!.data.forEach((row, rowIndex) => {
      if ('members' in row) {
        const actualCluster = data[rowIndex] as Cluster;
        row.members.forEach((member, memberIndex) => {
          expect(actualCluster.members?.[memberIndex]).toBe(member);
        });
      } else expect(data[rowIndex]).toBe(row);
    });
  });
  return actual;
}

function mixedEvents(): LiveEvent[] {
  const rows = ORDERED_CATEGORIES.flatMap((category, index) =>
    (['exact', 'city', 'admin1'] as const).flatMap((precision) =>
      Array.from({ length: 3 }, (_, member) =>
        liveEvent({
          id: `${category}-${precision}-${member}`,
          category,
          geo_confidence: precision,
          source_id: category === 'news' ? 'gdelt_news' : 'synthetic',
          subtype:
            category === 'maritime'
              ? 'vessel_position'
              : category === 'conflict'
                ? 'battle'
                : 'event',
          point: { lon: index - 5, lat: index - 5 },
          severity: member === 0 ? null : member / 2,
          attributes: member % 2 ? { track_deg: 30 } : {},
        }),
      ),
    ),
  );
  rows.push(
    liveEvent({ id: 'unlocated', point: null }),
    liveEvent({ id: 'invalid', point: { lon: NaN, lat: 0 } }),
    liveEvent({ id: 'outside', point: { lon: 181, lat: 0 } }),
    liveEvent({ id: 'country', geo_confidence: 'country' }),
    liveEvent({ id: 'wildfire', subtype: 'wildfire', geo_confidence: 'city' }),
    liveEvent({ id: 'thermal', subtype: 'thermal_detection', geo_confidence: 'admin1' }),
  );
  return rows;
}

it.each([undefined, 0, 1.499, 1.5, 2.499, 2.5, 2.999, 3, 12, 13])(
  'preserves ordered layers, exact cluster values and current references at zoom %s',
  (zoom) => {
    const events = mixedEvents();
    const view = zoom === undefined ? undefined : { zoom, globe: true, onCluster: vi.fn() };
    for (const hidden of [[], ['disaster', 'space'], [...ORDERED_CATEGORIES]] as Category[][]) {
      assertEquivalent(events, hidden, 'conflict-city-1', view);
      assertEquivalent([...events].reverse(), hidden, 'news-exact-1', view);
    }
  },
);

it.each([0, 1, 249, 250, 251])(
  'preserves the traffic quota and selected exception with %i rows',
  (size) => {
    const events = Array.from({ length: size }, (_, index) =>
      liveEvent({
        id: `traffic-${index}`,
        category: index % 2 ? 'aviation' : 'maritime',
        subtype: 'vessel_position',
        point: { lon: 0, lat: 0 },
        attributes: index % 3 ? { track_deg: 90 } : {},
      }),
    );
    const selected = events.at(-1)?.id ?? 'absent';
    const view = { zoom: 0, onCluster: vi.fn() };
    assertEquivalent(events, [], selected, view);
    assertEquivalent(events, [], null, view);
    if (size === 251) {
      const icons = buildEventLayers(events, [], vi.fn(), selected, view).find(
        (layer) => layer.id === 'event-icons',
      );
      // The reserved 250 include the selection; an unclustered remainder stays visible.
      expect(icons?.props.data).toHaveLength(251);
      expect(icons?.props.data).toHaveProperty('249', events.at(-1));
    }
  },
);

it('keeps the first visible duplicate selection and reads corrected fields afresh', () => {
  const hidden = liveEvent({ id: 'chosen', point: null });
  const first = liveEvent({ id: 'chosen', category: 'aviation', point: { lon: 0, lat: 0 } });
  const later = liveEvent({ id: 'chosen', category: 'cyber', geo_confidence: 'city' });
  const rows = [hidden, first, later, ...mixedEvents()];
  const view = { zoom: 0, onCluster: vi.fn() };
  let layers = assertEquivalent(rows, [], 'chosen', view);
  expect(layers.at(-1)?.props.data).toEqual([first]);
  first.category = 'maritime';
  first.subtype = 'vessel_position';
  first.attributes.track_deg = 45;
  first.geo_confidence = 'city';
  first.point = { lon: 179.99, lat: 89.9 };
  assertEquivalent(rows, [], 'chosen', view);
  first.source_id = 'gdelt_news';
  first.category = 'news';
  assertEquivalent(rows, [], 'chosen', view);
  first.category = 'conflict';
  first.attributes.conflict_screening = 'llm';
  first.attributes.conflict_relevance = 'military_activity';
  assertEquivalent(rows, [], 'chosen', view);
  first.point = null;
  layers = assertEquivalent(rows, [], 'chosen', view);
  expect(layers.at(-1)?.props.data).toEqual([later]);
  const replacement = liveEvent({ ...later, point: { lon: -179.99, lat: -89.9 }, severity: 1 });
  assertEquivalent([replacement, ...rows.slice(3)], [], 'chosen', view);
  assertEquivalent(
    rows.filter((row) => row.id !== 'chosen'),
    [],
    'chosen',
    view,
  );
});

it('retains layer picking, accessors and frozen input ownership', () => {
  const exact = liveEvent({ id: 'point', point: { lon: 1, lat: 2 } });
  const approximate = liveEvent({ id: 'ring', category: 'cyber', geo_confidence: 'city' });
  const rows = [exact, approximate];
  for (const event of rows) {
    Object.freeze(event.attributes);
    Object.freeze(event.tags);
    Object.freeze(event.point);
    Object.freeze(event);
  }
  assertEquivalent(Object.freeze(rows), [], exact.id);
  const onPick = vi.fn();
  const layers = buildEventLayers(rows, [], onPick, exact.id);
  for (const id of ['events-disaster', 'approximate-events', 'event-icons']) {
    const layer = layers.find((item) => item.id === id)!;
    const getPosition: unknown = Reflect.get(layer.props, 'getPosition');
    const onClick: unknown = Reflect.get(layer.props, 'onClick');
    if (typeof getPosition !== 'function' || typeof onClick !== 'function')
      throw new Error('Expected position and picking callbacks');
    const event = id === 'events-disaster' ? exact : approximate;
    expect(Reflect.apply(getPosition, layer.props, [event])).toEqual([
      event.point!.lon,
      event.point!.lat,
    ]);
    expect(Reflect.apply(onClick, layer.props, [{ object: event, x: 10, y: 20 }])).toBe(true);
    expect(onPick).toHaveBeenLastCalledWith(event, [10, 20]);
  }
});

it('prepares exact rows without repeating whole-population precision classification', () => {
  let precisionReads = 0;
  const events = Array.from({ length: 5000 }, (_, index) => {
    const event = liveEvent({
      id: `plane-${index}`,
      category: 'aviation',
      point: { lon: 0, lat: 0 },
    });
    Object.defineProperty(event, 'geo_confidence', {
      get: () => {
        precisionReads += 1;
        return 'exact';
      },
    });
    return event;
  });
  const view = { zoom: 0, onCluster: vi.fn() };
  const expected = reference(events, [], null, view);
  expect(precisionReads).toBeGreaterThan(events.length * 2);
  precisionReads = 0;
  const actual = buildEventLayers(events, [], vi.fn(), null, view);
  expect(precisionReads).toBeLessThanOrEqual(events.length * 2);
  expect(actual.map((layer) => ({ id: layer.id, data: layer.props.data }))).toEqual(expected);
});
