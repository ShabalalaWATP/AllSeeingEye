import { expect, it, vi } from 'vitest';
import { countries, liveEvent } from '@/test/fixtures';
import type { Country } from '@/lib/api/geoSchemas';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { cyberCountryGroups } from './cyberCountryContext';
import { cyberCountryLayers } from './layers/cyberCountries';
import { buildEventLayers } from './layers/registry';
import { iconFor } from './layers/icons';

const directory = Object.fromEntries(countries.map((country) => [country.iso2, country]));
const claim = liveEvent({
  id: 'claim',
  category: 'cyber',
  subtype: 'ransomware',
  country_iso: 'GB',
  geo_confidence: 'country',
  point: null,
});

it('groups only evidenced country context and leaves unknown or publisher geography unplotted', () => {
  const events = [
    claim,
    { ...claim, id: 'second', subtype: 'outage' },
    { ...claim, id: 'publisher', subtype: 'advisory' },
    { ...claim, id: 'unknown', country_iso: 'XX' },
  ];
  const groups = cyberCountryGroups(events, directory);
  expect(groups).toHaveLength(1);
  expect(groups[0]?.events.map((event) => event.id)).toEqual(['claim', 'second']);
  expect(claim.point).toBeNull();
  expect(buildEventLayers(events, [], vi.fn(), null)).toEqual([]);
  const invalid = {
    ...directory,
    GB: { ...directory.GB!, centroid: [NaN, 0] as [number, number] },
  };
  expect(cyberCountryGroups([claim], invalid)).toEqual([]);
});

it.each([true, false])(
  'labels every country reference and keeps selectable contexts separate from incident geometry (flat=%s)',
  (flat) => {
    const groups = cyberCountryGroups([claim], directory);
    const select = vi.fn();
    const layers = cyberCountryLayers(groups, groups[0]!, select, flat);
    expect(layers.every((layer) => layer.id.startsWith('cyber-country-context-'))).toBe(true);
    const labels = layers.find((layer) => layer.id.endsWith('labels'))!;
    expect(labels.props).toMatchObject({ billboard: flat, pickable: false });
    const props = labels.props as unknown as {
      getText: (item: (typeof groups)[0]) => string;
      getPosition: (item: (typeof groups)[0]) => number[];
    };
    expect(props.getText(groups[0]!)).toBe('GB · 1\nCYBER COUNTRY CONTEXT');
    expect(props.getPosition(groups[0]!)).toEqual(directory.GB!.centroid);
    const click = layers[1]!.props as unknown as { onClick: (info: { object?: unknown }) => void };
    click.onClick({ object: groups[0] });
    expect(select).toHaveBeenCalledWith(groups[0]);
    click.onClick({});
    expect(select).toHaveBeenCalledTimes(1);
    expect(cyberCountryLayers([], null, select, flat)).toEqual([]);
  },
);

it('renders shields only for genuinely located cyber events and preserves approximate rings and picks', () => {
  const exact = {
    ...claim,
    id: 'reported',
    point: { lon: 1, lat: 2 },
    geo_confidence: 'exact' as const,
  };
  const approximate = { ...exact, id: 'city', geo_confidence: 'city' as const };
  const pick = vi.fn();
  const layers = buildEventLayers([exact, approximate, claim], [], pick, exact.id);
  const icons = layers.find((layer) => layer.id === 'event-icons')!;
  expect(iconFor(exact)).toBe('cyber');
  expect(icons.props.data).toEqual([exact, approximate]);
  expect(layers.find((layer) => layer.id === 'approximate-events')?.props.data).toEqual([
    approximate,
  ]);
  const props = icons.props as unknown as { onClick: (info: { object: LiveEvent }) => void };
  props.onClick({ object: exact });
  expect(pick).toHaveBeenCalledWith(exact);
  expect(buildEventLayers([exact, approximate], ['cyber'], pick, null)).toEqual([]);
});

it('caps country context groups independently of oversized upstream catalogues', () => {
  const many: Record<string, Country> = {};
  const events = Array.from({ length: 260 }, (_, index) => {
    const iso = String(index);
    many[iso] = { ...directory.GB!, iso2: iso };
    return { ...claim, id: iso, country_iso: iso };
  });
  expect(cyberCountryGroups(events, many)).toHaveLength(250);
});
