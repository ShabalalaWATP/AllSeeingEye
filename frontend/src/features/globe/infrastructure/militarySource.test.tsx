import { act, render, renderHook, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { Country } from '@/lib/api/geoSchemas';
import { InfrastructureInspector } from './InfrastructureInspector';
import { InfrastructurePanel } from './InfrastructurePanel';
import { buildInfrastructureLayers } from './infrastructureLayers';
import { useInfrastructure } from './useInfrastructure';

const countries: Record<string, Country> = {
  CA: {
    iso2: 'CA',
    iso3: 'CAN',
    name: 'Canada',
    bounds: [-141, 42, -52, 84],
    centroid: [-100, 60],
  },
  UA: {
    iso2: 'UA',
    iso3: 'UKR',
    name: 'Ukraine',
    bounds: [22, 44, 41, 52],
    centroid: [31, 49],
  },
};

it('keeps military source badges off by default and shows only country references', () => {
  const { result } = renderHook(() => useInfrastructure(countries));
  expect(result.current.militaryEnabled).toBe(false);
  expect(result.current.militaryCountries).toHaveLength(2);
  expect(result.current.militaryCountries[0]).not.toHaveProperty('latitude');
  expect(
    buildInfrastructureLayers({ ...result.current, militaryEnabled: false }, vi.fn(), true),
  ).toEqual([]);

  act(() => result.current.toggleMilitary());
  expect(result.current.data).toBeNull();
  const pick = vi.fn();
  const layers = buildInfrastructureLayers(result.current, pick, true);
  expect(layers.map((layer) => layer.id)).toEqual([
    'military-source-countries',
    'military-source-country-labels',
    'military-source-country-captions',
  ]);
  expect(layers[0]!.props.pickable).toBe(true);
  (layers[0]!.props.onClick as (info: unknown) => boolean)({
    object: result.current.militaryCountries[0],
  });
  expect(pick).toHaveBeenCalledWith({
    kind: 'military_country',
    item: result.current.militaryCountries[0],
  });
});

it('opens official source details and removes the selection when closed or disabled', async () => {
  function Panel() {
    const state = useInfrastructure(countries);
    return (
      <>
        <InfrastructurePanel state={state} onSelect={state.select} />
        {state.selected && (
          <InfrastructureInspector selected={state.selected} onClose={state.close} />
        )}
      </>
    );
  }
  const user = userEvent.setup();
  render(<Panel />);
  const toggle = screen.getByRole('switch', { name: 'Military source index' });
  expect(toggle).toHaveAttribute('aria-checked', 'false');
  await user.click(toggle);
  expect(toggle).toHaveAttribute('aria-checked', 'true');
  await user.click(screen.getByRole('button', { name: /Canada.*official source/ }));
  const inspector = screen.getByRole('complementary', { name: 'Infrastructure details' });
  expect(inspector).toHaveTextContent('not a military base location');
  expect(
    screen.getByRole('link', { name: 'Canadian Armed Forces bases and support units' }),
  ).toHaveAttribute(
    'href',
    'https://www.canada.ca/en/department-national-defence/services/bases-support-units.html',
  );
  await user.click(screen.getByRole('button', { name: 'Close infrastructure details' }));
  expect(screen.queryByRole('complementary', { name: 'Infrastructure details' })).toBeNull();
  await user.click(screen.getByRole('button', { name: /Ukraine.*official source/ }));
  await user.click(toggle);
  expect(screen.queryByRole('complementary', { name: 'Infrastructure details' })).toBeNull();
});
