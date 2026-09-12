import { act, renderHook } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { countries, liveEvent } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { prepareCyberMap, useCyberFiltersStore } from '@/stores/cyberFilters';
import { useCyberMapSelection } from './useCyberMapSelection';
import { useContextSelection } from './context/useContextSelection';
import { cyberCountryGroups } from './cyberCountryContext';
import type { GlobeEngineHandle } from './useGlobeEngine';
import type { LocationQualityFilter } from './geographicPrecision';

const directory = Object.fromEntries(countries.map((country) => [country.iso2, country]));
const claim = liveEvent({
  category: 'cyber',
  subtype: 'ransomware',
  country_iso: 'GB',
  geo_confidence: 'country',
  point: null,
  published_at: new Date().toISOString(),
});
const groups = cyberCountryGroups([claim], directory);
const cyber = {
  events: [claim],
  groups,
  selected: null,
  close: vi.fn(),
  select: vi.fn(),
  refresh: vi.fn(),
  loading: false,
  fetchedAt: null,
  error: null,
  limited: false,
};

function harness() {
  const flyTo = vi.fn();
  const engine = { flyTo } as unknown as GlobeEngineHandle;
  const closeOthers = vi.fn();
  const hook = renderHook(
    ({ enabled, picking, quality, countries }) => {
      const context = useContextSelection(null, picking, 'globe');
      const selection = useCyberMapSelection({
        cyber,
        enabled,
        picking,
        quality,
        countries,
        engine,
        closeOthers,
        mode: 'globe',
        context,
        windowHours: 48,
        now: Date.now(),
      });
      return { ...selection, context };
    },
    {
      initialProps: {
        enabled: true,
        picking: false,
        quality: 'all' as LocationQualityFilter,
        countries: directory,
      },
    },
  );
  return { ...hook, flyTo, closeOthers };
}

it('focuses precise evidence with a globe shield and clears it when a location-quality filter excludes it', () => {
  applySession('user');
  const { result, rerender, flyTo, closeOthers } = harness();
  const exact = { ...claim, point: { lon: 7, lat: 8 }, geo_confidence: 'exact' as const };
  act(() => result.current.selectRecord(exact));
  expect(flyTo).toHaveBeenLastCalledWith({ center: [7, 8], zoom: 5 });
  expect(closeOthers).toHaveBeenCalled();
  expect(
    result.current.context.layers.find((layer) => layer.id === 'context-selected-cyber')?.props,
  ).toMatchObject({ billboard: false, pickable: false });
  rerender({ enabled: true, picking: false, quality: 'unplotted', countries: directory });
  expect(result.current.context.event).toBeNull();
  act(() => result.current.selectGroup(groups[0]!));
  expect(cyber.select).toHaveBeenCalledWith('GB');
  rerender({ enabled: true, picking: true, quality: 'all', countries: directory });
  const calls = flyTo.mock.calls.length;
  act(() => {
    result.current.selectRecord(exact);
    result.current.selectGroup(groups[0]!);
  });
  expect(flyTo).toHaveBeenCalledTimes(calls);
  rerender({ enabled: false, picking: false, quality: 'all', countries: directory });
  expect(result.current.layers).toEqual([]);
});

it('consumes explicit country navigation once and drops stale authority requests', () => {
  applySession('user');
  prepareCyberMap({ country: 'GB' });
  const { result, rerender, flyTo } = harness();
  expect(flyTo).toHaveBeenCalledWith(expect.objectContaining({ center: directory.GB!.centroid }));
  expect(useCyberFiltersStore.getState().pending).toBeNull();
  act(() =>
    useCyberFiltersStore.setState({
      pending: { authority: 'previous-session', country: 'GB', event: claim },
    }),
  );
  expect(result.current.context.event).toBeNull();
  expect(useCyberFiltersStore.getState().pending).toBeNull();
  rerender({ enabled: true, picking: false, quality: 'all', countries: {} });
  act(() => {
    prepareCyberMap({ country: 'GB', event: claim });
  });
  expect(useCyberFiltersStore.getState().pending).not.toBeNull();
  rerender({ enabled: true, picking: false, quality: 'all', countries: directory });
  expect(result.current.context.event).toBe(claim);
  expect(useCyberFiltersStore.getState().pending).toBeNull();
});

it('does not infer navigation for unlocated advisories and rejects excluded kinds', () => {
  applySession('user');
  const { result, flyTo } = harness();
  const advisory = { ...claim, subtype: 'advisory', geo_confidence: 'none' as const };
  act(() => result.current.selectRecord(advisory));
  expect(result.current.context.event).toBe(advisory);
  expect(flyTo).not.toHaveBeenCalled();
  act(() => useCyberFiltersStore.getState().setKind('outage_signal'));
  expect(result.current.context.event).toBeNull();
  act(() => result.current.selectRecord(advisory));
  expect(result.current.context.event).toBeNull();
});

it('highlights the selected list record country reference and clears it when details close or filters exclude it', () => {
  applySession('user');
  const { result } = harness();
  const lineColour = () => {
    const props = result.current.layers.find(
      (layer) => layer.id === 'cyber-country-context-badges',
    )!.props as unknown as { getLineColor: (group: (typeof groups)[number]) => number[] };
    return props.getLineColor(groups[0]!);
  };
  const unselected = [34, 211, 238, 220];
  expect(lineColour()).toEqual(unselected);
  act(() => result.current.selectRecord(claim));
  expect(result.current.context.event).toBe(claim);
  expect(result.current.context.layers).toEqual([]);
  expect(cyber.selected).toBeNull();
  expect(lineColour()).toEqual([255, 255, 255, 255]);
  act(() => result.current.context.close());
  expect(lineColour()).toEqual(unselected);
  act(() => result.current.selectRecord({ ...claim, id: 'outside-current-context' }));
  expect(lineColour()).toEqual(unselected);
  act(() => result.current.selectRecord(claim));
  expect(lineColour()).toEqual([255, 255, 255, 255]);
  act(() => useCyberFiltersStore.getState().setKind('outage_signal'));
  expect(lineColour()).toEqual(unselected);
});
